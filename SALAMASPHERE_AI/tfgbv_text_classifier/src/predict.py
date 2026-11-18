"""Local inference for the validation-selected Kiswahili offensive-language baseline."""

from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib


ROOT = Path(__file__).resolve().parents[1]
MODEL_CONFIG_PATH = ROOT / "reports" / "selected_model.json"
MAX_INPUT_CHARACTERS = 10_000
GENERAL_LIMITATION = (
    "General Kiswahili offensive-language baseline only; not a validated TFGBV detector. "
    "Do not use this prediction to determine report credibility, deny help, or replace human review."
)


def preprocess_text(text: str) -> str:
    """Make text safe for the vectorizer without removing meaningful tokens."""
    # Replace unpaired surrogate code points that cannot be encoded as UTF-8.
    safe = "".join("\ufffd" if 0xD800 <= ord(char) <= 0xDFFF else char for char in text)
    return safe.encode("utf-8", errors="replace").decode("utf-8")


@lru_cache(maxsize=1)
def _load_bundle() -> tuple[Any, dict[str, Any]]:
    if not MODEL_CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Model configuration not found: {MODEL_CONFIG_PATH}")
    config = json.loads(MODEL_CONFIG_PATH.read_text(encoding="utf-8"))
    artifact = (ROOT / config["artifact"]).resolve()
    if not artifact.is_relative_to(ROOT.resolve()):
        raise ValueError("Configured model artifact must be inside the project directory.")
    if not artifact.is_file():
        raise FileNotFoundError(f"Model artifact not found: {artifact}")
    return joblib.load(artifact), config


def _result(
    *,
    predicted_label: str | None,
    label_id: int | None,
    score: float | None,
    threshold: float | None,
    version: str,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "predicted_label": predicted_label,
        "label_id": label_id,
        "offensive_score": score,
        "score_type": "unbounded LinearSVC decision margin; not a probability",
        "threshold": threshold,
        "model_version": version,
        "warning": warnings,
    }


def predict_text(text: str) -> dict[str, Any]:
    """Return an offensive-language baseline prediction and safety limitations."""
    model, config = _load_bundle()
    threshold = float(config["threshold"])
    version = str(config["model_version"])
    warnings = [GENERAL_LIMITATION]

    if text is None:
        warnings.append("Input is None; no prediction was made.")
        return _result(predicted_label=None, label_id=None, score=None,
                       threshold=threshold, version=version, warnings=warnings)
    if not isinstance(text, str):
        warnings.append("Input must be a string; no prediction was made.")
        return _result(predicted_label=None, label_id=None, score=None,
                       threshold=threshold, version=version, warnings=warnings)

    safe_text = preprocess_text(text)
    if not safe_text.strip():
        warnings.append("Input is empty or whitespace only; no prediction was made.")
        return _result(predicted_label=None, label_id=None, score=None,
                       threshold=threshold, version=version, warnings=warnings)
    if len(safe_text) > MAX_INPUT_CHARACTERS:
        safe_text = safe_text[:MAX_INPUT_CHARACTERS]
        warnings.append(f"Input was truncated to {MAX_INPUT_CHARACTERS} characters.")

    score = float(model.decision_function([safe_text])[0])
    label_id = int(score >= threshold)
    label = "offensive" if label_id == 1 else "non_offensive"
    return _result(predicted_label=label, label_id=label_id, score=score,
                   threshold=threshold, version=version, warnings=warnings)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", help="Kiswahili text to classify. If omitted, prompt interactively.")
    args = parser.parse_args()
    text = args.text if args.text is not None else input("Enter text: ")
    print(json.dumps(predict_text(text), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
