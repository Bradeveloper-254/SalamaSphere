"""Inspect the Swahili offensive-text dataset and write clean, decontaminated splits."""

from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
from datasets import load_dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors


DATASET_NAME = "metabloit/offensive-swahili-text"
LABEL_DEFINITIONS = {0: "non-offensive", 1: "offensive"}
ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
PROCESSED_DIR = ROOT / "Data" / "processed"
NEAR_COSINE_THRESHOLD = 0.90
NEAR_SEQUENCE_THRESHOLD = 0.90


def normalize_text(value: object) -> str:
    """Normalize Unicode, case, and whitespace for duplicate/leakage checks."""
    if pd.isna(value):
        return ""
    return " ".join(unicodedata.normalize("NFKC", str(value)).casefold().split())


def near_duplicate_mask(
    query: pd.DataFrame,
    reference: pd.DataFrame,
    vectorizer: TfidfVectorizer,
) -> pd.Series:
    """Find conservative near duplicates using char similarity plus sequence ratio."""
    if query.empty or reference.empty:
        return pd.Series(False, index=query.index)
    reference_vectors = vectorizer.transform(reference["text"].astype(str))
    query_vectors = vectorizer.transform(query["text"].astype(str))
    neighbor = NearestNeighbors(n_neighbors=1, metric="cosine", algorithm="brute", n_jobs=-1)
    neighbor.fit(reference_vectors)
    distances, indices = neighbor.kneighbors(query_vectors)
    matches = []
    for row_index, (distance, reference_index) in enumerate(zip(distances[:, 0], indices[:, 0])):
        query_text = str(query["text"].iloc[row_index])
        reference_text = str(reference["text"].iloc[int(reference_index)])
        cosine_similarity = 1.0 - float(distance)
        sequence_similarity = SequenceMatcher(None, query_text, reference_text).ratio()
        matches.append(
            cosine_similarity >= NEAR_COSINE_THRESHOLD
            and sequence_similarity >= NEAR_SEQUENCE_THRESHOLD
        )
    return pd.Series(matches, index=query.index)


def count_within_split_candidates(
    frame: pd.DataFrame, vectorizer: TfidfVectorizer,
) -> int:
    """Count rows with a conservative near neighbor inside their own split."""
    if len(frame) < 2:
        return 0
    vectors = vectorizer.transform(frame["text"].astype(str))
    neighbor = NearestNeighbors(n_neighbors=2, metric="cosine", algorithm="brute", n_jobs=-1)
    neighbor.fit(vectors)
    distances, indices = neighbor.kneighbors(vectors)
    count = 0
    for row_index, (distance, neighbor_index) in enumerate(zip(distances[:, 1], indices[:, 1])):
        similarity = 1.0 - float(distance)
        text = str(frame["text"].iloc[row_index])
        other = str(frame["text"].iloc[int(neighbor_index)])
        if similarity >= NEAR_COSINE_THRESHOLD and SequenceMatcher(None, text, other).ratio() >= NEAR_SEQUENCE_THRESHOLD:
            count += 1
    return count


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(DATASET_NAME)
    frames: dict[str, pd.DataFrame] = {
        name: split.to_pandas().loc[:, ["text", "labels"]].copy()
        for name, split in dataset.items()
    }
    required_splits = {"train", "validation", "test"}
    if set(frames) != required_splits:
        raise ValueError(f"Expected splits {sorted(required_splits)}, got {sorted(frames)}")

    for name, frame in frames.items():
        unknown = set(frame["labels"].dropna().unique()) - set(LABEL_DEFINITIONS)
        if unknown:
            raise ValueError(f"Unexpected labels in {name}: {sorted(unknown)}")
        frame["_normalized_text"] = frame["text"].map(normalize_text)

    print("=" * 72)
    print("SALAMASPHERE AI - DATASET QUALITY INSPECTION")
    print(f"Dataset: {DATASET_NAME}")
    print("Source: JamiiForums comments scraped using a prepared abusive-word list.")
    print("Card scope: abusive words in that word list; sarcastic abuse is explicitly not covered.")
    print("Labels: " + ", ".join(f"{label}={meaning}" for label, meaning in LABEL_DEFINITIONS.items()))
    print("Dataset card license: MIT (uploader-declared; see DATA_SOURCES.md caveat).")

    global_labels = pd.concat(
        [frame.loc[frame["_normalized_text"] != "", ["_normalized_text", "labels"]]
         for frame in frames.values()],
        ignore_index=True,
    )
    labels_per_text = global_labels.groupby("_normalized_text")["labels"].nunique()
    conflict_texts = set(labels_per_text[labels_per_text > 1].index)

    print("\n--- RAW SPLIT QUALITY ---")
    summary: dict[str, dict[str, int]] = {}
    for name, frame in frames.items():
        blank_count = int((frame["_normalized_text"] == "").sum())
        nonblank = frame.loc[frame["_normalized_text"] != ""]
        local_group_counts = nonblank.groupby("_normalized_text")["labels"].nunique()
        summary[name] = {
            "raw_rows": len(frame),
            "empty_or_blank": blank_count,
            "exact_duplicate_rows": int(frame["text"].duplicated().sum()),
            "normalized_duplicate_rows": int(nonblank["_normalized_text"].duplicated().sum()),
            "conflicting_label_rows": int(nonblank["_normalized_text"].isin(conflict_texts).sum()),
        }
        print(f"\n{name}: {len(frame)} rows; labels {frame['labels'].value_counts().sort_index().to_dict()}")
        print(f"  empty/blank: {blank_count}")
        print(f"  exact duplicate rows after first occurrence: {summary[name]['exact_duplicate_rows']}")
        print(f"  normalized duplicate rows after first occurrence: {summary[name]['normalized_duplicate_rows']}")
        print(f"  rows in globally conflicting-label groups: {summary[name]['conflicting_label_rows']}")

    if conflict_texts:
        print(f"\nConflicting texts found: {len(conflict_texts)}; excluding these groups from all cleaned splits.")

    # Remove blanks and ambiguous examples, then deduplicate within each split.
    candidates: dict[str, pd.DataFrame] = {}
    for name, frame in frames.items():
        clean = frame.loc[frame["_normalized_text"] != ""].copy()
        clean = clean.loc[~clean["_normalized_text"].isin(conflict_texts)]
        clean = clean.drop_duplicates(subset="_normalized_text", keep="first")
        candidates[name] = clean

    # Keep held-out examples; test takes precedence over validation, and both
    # held-out splits take precedence over training to prevent leakage.
    # Character similarity flags spelling/edit variants that exact normalization
    # cannot catch. Require both high cosine and high sequence similarity to avoid
    # dropping short messages that merely share common character n-grams.
    all_candidate_text = pd.concat(
        [candidate["text"].astype(str) for candidate in candidates.values()],
        ignore_index=True,
    )
    near_vectorizer = TfidfVectorizer(
        analyzer="char", ngram_range=(3, 5), min_df=2,
        max_features=50_000, sublinear_tf=True,
    ).fit(all_candidate_text)
    within_near_candidates = {
        name: count_within_split_candidates(candidate, near_vectorizer)
        for name, candidate in candidates.items()
    }

    test_texts = set(candidates["test"]["_normalized_text"])
    validation = candidates["validation"].loc[
        ~candidates["validation"]["_normalized_text"].isin(test_texts)
    ].copy()
    validation_near_test = near_duplicate_mask(validation, candidates["test"], near_vectorizer)
    validation_near_test_count = int(validation_near_test.sum())
    validation = validation.loc[~validation_near_test].copy()
    held_out_texts = test_texts | set(validation["_normalized_text"])
    train = candidates["train"].loc[
        ~candidates["train"]["_normalized_text"].isin(held_out_texts)
    ].copy()
    held_out = pd.concat([candidates["test"], validation], ignore_index=True)
    train_near_held_out = near_duplicate_mask(train, held_out, near_vectorizer)
    train_near_held_out_count = int(train_near_held_out.sum())
    train = train.loc[~train_near_held_out].copy()
    cleaned = {"train": train, "validation": validation, "test": candidates["test"]}

    print("\n--- CLEANING RESULTS ---")
    output_rows = []
    for name, frame in cleaned.items():
        output = frame.loc[:, ["text", "labels"]].reset_index(drop=True)
        output_path = PROCESSED_DIR / f"{name}.csv"
        output.to_csv(output_path, index=False, encoding="utf-8")
        metrics = summary[name]
        metrics["clean_rows"] = len(output)
        metrics["removed_total"] = metrics["raw_rows"] - len(output)
        metrics["near_duplicate_rows_removed"] = (
            train_near_held_out_count if name == "train"
            else validation_near_test_count if name == "validation"
            else 0
        )
        metrics["within_split_near_neighbor_rows_flagged_not_removed"] = within_near_candidates[name]
        metrics["clean_label_0"] = int((output["labels"] == 0).sum())
        metrics["clean_label_1"] = int((output["labels"] == 1).sum())
        output_rows.append({"split": name, **metrics})
        print(f"{name}: {len(output)} clean rows -> {output_path.relative_to(ROOT)}")

    split_sets = {
        name: set(frame["_normalized_text"])
        for name, frame in cleaned.items()
    }
    overlaps = {
        "train_validation": split_sets["train"] & split_sets["validation"],
        "train_test": split_sets["train"] & split_sets["test"],
        "validation_test": split_sets["validation"] & split_sets["test"],
    }
    remaining_near = {
        "train_validation": int(near_duplicate_mask(cleaned["train"], cleaned["validation"], near_vectorizer).sum()),
        "train_test": int(near_duplicate_mask(cleaned["train"], cleaned["test"], near_vectorizer).sum()),
        "validation_test": int(near_duplicate_mask(cleaned["validation"], cleaned["test"], near_vectorizer).sum()),
    }
    report_path = REPORT_DIR / "dataset_quality_report.csv"
    pd.DataFrame(output_rows).to_csv(report_path, index=False, encoding="utf-8")
    print("\n--- CLEANED CROSS-SPLIT OVERLAP ---")
    print(f"Near-duplicate train rows removed against held-out splits: {train_near_held_out_count}")
    print(f"Near-duplicate validation rows removed against test: {validation_near_test_count}")
    for pair, overlap in overlaps.items():
        print(f"{pair.replace('_', ' vs ')}: {len(overlap)}")
    print("Within-split near-neighbor rows flagged (not removed):", within_near_candidates)
    print("Remaining cross-split near-duplicate candidates:", remaining_near)
    if any(overlaps.values()):
        raise RuntimeError("Cleaned splits still share normalized messages.")
    if any(remaining_near.values()):
        raise RuntimeError("Cleaned splits still share high-similarity message candidates.")

    print(f"\nSummary report: {report_path.relative_to(ROOT)}")
    print("Inspection and cleaning completed.")


if __name__ == "__main__":
    main()
