# Proposed TFGBV dataset schema and data dictionary

**Status:** Proposed for review; not an approved collection specification. No TFGBV records are present or collected under this proposal. **Version:** 0.1. See [protocol](tfgbv_research_protocol.md) and [annotation handbook](annotation_guidelines_draft.md).

The default research table is minimized and text-only. It must not contain names, phone numbers, email addresses, exact addresses, account handles, profile URLs, or direct identifiers. Do not store raw audio or images in this dataset. The example values below are synthetic and do not represent collected records. Fields marked conditionally required become required only if a source is approved and the field is necessary.

## Record-level fields

| Field | Type / required | Allowed values | Description / synthetic example | Privacy considerations |
|---|---|---|---|---|
| `record_id` | string / required | Random UUID-like opaque ID | `rec-7f2c` | Never encode source ID, username, date, or label. |
| `source_id` | string / optional restricted linkage | Opaque source-register key | `SRC-003` | Keep linkage separately with restricted access; omit from released annotation table if unnecessary. |
| `source_category` | enum / required | `approved_corpus`, `voluntary_contribution`, `approved_public_material`, `other_approved` | `approved_corpus` | Category only; do not expose platform/account. |
| `provenance_ref` | string / conditionally required | Controlled source register reference | `prov-014` | Restricted register; no public URLs or identity-bearing references in routine table. |
| `collection_date_range` | string / optional | Coarse approved period, e.g. `2025-Q1` | `2025-Q1` | Avoid exact timestamps unless justified; can identify a person when combined with source. |
| `language_id` | enum / required | `sw`, `en`, `sheng`, `other`, `undetermined` | `sw` | Linguistic attribute may reveal community; use only for research. |
| `language_mixture` | array of enum / required | Any combination of `sw`, `en`, `sheng`, `other`, or `none` | `["sw","en"]` | Do not infer ability from this field. |
| `text_content` | string / conditional | Minimized approved text | `Synthetic: “I will share your private photo unless you pay.”` | Sensitive content. Keep in access-controlled environment; redact identifiers before annotator access. Prefer `protected_text_ref` when table access is broader. |
| `protected_text_ref` | string / conditional | Opaque vault locator | `vault-item-0041` | Locator access must be controlled; never a public URL or filesystem path revealing identity. |
| `primary_label` | enum / required after annotation | One label or `uncertain_insufficient_context`; `non_tfgbv` only if sufficient context supports it | `sexual_extortion` | Do not force uncertain items into a TFGBV class. |
| `secondary_labels` | array / required after annotation | Zero or more labels from handbook taxonomy | `["blackmail"]` | Multi-label; exclude `non_tfgbv` alongside confirmed TFGBV labels. |
| `discourse_role` | enum / required after annotation | `apparently_perpetrating`, `quoting_or_reporting`, `counterspeech_or_support`, `educational_or_news_discussion`, `unclear` | `apparently_perpetrating` | Describes text, not verified actor identity. |
| `target_type` | enum / optional | `individual`, `group`, `self`, `unclear`, `not_applicable` | `individual` | Avoid target identity or demographic inference. |
| `gender_basis` | enum / optional | `explicit_in_text`, `context_supported`, `unclear`, `not_applicable` | `explicit_in_text` | Do not infer from names/profile/stereotypes. |
| `explicitness` | enum / optional proposed | `direct`, `indirect`, `quoted_only`, `unclear`, `not_applicable` | `direct` | Operational definitions require reviewer approval; not a risk/severity score. |
| `severity` | enum / optional, disabled by default | `not_assessed` until purpose and anchors approved | `not_assessed` | No scale is proposed for routine annotation; add only with validated purpose, definitions, and review. |
| `context_sufficiency` | enum / required | `sufficient`, `insufficient`, `uncertain` | `sufficient` | Indicates evidence available to annotator, not event truth. |
| `uncertainty_reasons` | array / conditionally required | `missing_context`, `ambiguous_target`, `ambiguous_language`, `sarcasm_or_irony`, `quotation_or_report`, `consent_unclear`, `gender_basis_unclear`, `translation_uncertain`, `other` | `["consent_unclear"]` | Free-text notes may reveal sensitive details; use codes. |
| `annotator_id` | pseudonymous string / required per vote | Project-issued random pseudonym | `ann-12` | Keep identity key separate and access restricted; do not use initials/email. |
| `annotation_timestamp` | datetime / required per vote | ISO 8601, access-controlled | `2026-02-10T09:00:00Z` | Consider date-only/coarsened timestamp in analysis exports. |
| `annotator_confidence` | enum / required per vote | `high`, `medium`, `low` | `medium` | Confidence is subjective annotation confidence, not probability or case credibility. |
| `annotator_rationale` | short string / optional | Minimized, structured rationale preferred | `Synthetic explanation: demand backed by exposure threat.` | Never copy unnecessary text or identifiers; keep restricted. |
| `disagreement_status` | enum / required | `not_applicable`, `pending`, `resolved`, `retained_uncertain`, `taxonomy_gap`, `excluded` | `pending` | Preserve votes; do not present adjudication as truth. |
| `adjudicated_label_set` | array / conditional | Approved taxonomy labels | `["sexual_extortion","blackmail"]` | Store with adjudicator pseudonym and rationale under restricted access. |
| `adjudicator_id` | pseudonymous string / conditional | Project-issued pseudonym | `adj-02` | Identity key separate. |
| `adjudication_timestamp` | datetime / conditional | ISO 8601 | `2026-02-12T11:00:00Z` | Minimize precision in analysis exports. |
| `consent_permission_status` | enum / conditionally required | `documented`, `not_applicable_with_basis`, `pending`, `not_obtained`, `withdrawn` | `documented` | Never treat blank as approval. Supporting evidence lives in restricted source register. |
| `privacy_review_status` | enum / required before annotation | `pending`, `passed_minimized`, `excluded`, `needs_review` | `passed_minimized` | Must be completed before annotator access. |
| `split_assignment` | enum / optional future evaluation | `train`, `validation`, `test`, `external_test`, `unassigned` | `unassigned` | Do not expose test labels/content to iterative model developers. |
| `dataset_version` | string / required | Semantic/revision identifier | `pilot-0.1` | Version is not a permission claim. |
| `record_status` | enum / required | `candidate`, `included`, `excluded`, `withdrawn`, `deleted` | `candidate` | Keep withdrawal/deletion audit minimal and non-identifying. |

### Field use notes

The handbook's full taxonomy is used across `primary_label`, `secondary_labels`, and the adjudicated label set. Multi-label co-occurrence is allowed as defined in the handbook. `uncertain_insufficient_context` is an uncertainty disposition and must not be conflated with a positive TFGBV finding or `non_tfgbv`. The proposed `severity` field is disabled by default; no severity scale should be introduced until purpose, operational anchors, limitations, and reviewer approval are documented. Text can be stored separately from labels for access control; avoid duplicating raw text across exports, logs, and annotation systems.

## Annotation vote table (recommended separation)

Store one row per annotator-record vote in a protected table keyed by `record_id` and pseudonymous `annotator_id`, with `primary_label`, `secondary_labels`, `discourse_role`, `target_type`, `gender_basis`, `context_sufficiency`, `uncertainty_reasons`, `annotator_confidence`, minimized rationale, and annotation timestamp. Keep adjudication in a separate table. This preserves independent judgments and prevents overwriting disagreement history.

## Source register template

One entry per source. Status starts `NOT STARTED`; no source is approved by inclusion in this template.

| Field | Required evidence / notes |
|---|---|
| `source_id` and source category | Opaque ID; avoid identity in general exports. |
| Source description and owner | Identify the source and responsible contact in restricted register. |
| Legitimacy and provenance | Document origin, chain of custody, source authenticity limits. |
| Source terms and copyright/license | Preserve terms/version and written permission; a dataset-card license may not cover underlying posts. |
| Privacy, consent, lawful basis | Qualified reviewer decision and evidence; public availability is not blanket permission. |
| Sensitivity and re-identification | Risks involving victims, minors, intimate content, and contextual linkage. |
| Collection method and date range | Method, dates, scope; any method requires approval first. |
| Research suitability and bias | Relevance, selection bias, language/source coverage limitations. |
| Permitted retention, annotation, publication, redistribution | Separate decisions for each use; explicit limitations and expiry. |
| Minimization and storage controls | Redaction plan, approved storage, encryption, access roles. |
| Decision | `pending`, `approved_with_conditions`, `rejected`, `expired`; evidence reference, reviewer, date. |

## Versioning and provenance strategy

Assign each approved dataset release a version and immutable manifest containing schema/guideline versions, source-register IDs, sampling code/version, date range at justified granularity, transformations, exclusion counts/reasons, annotation/adjudication procedure, split method, and aggregate language/label distributions. Keep hashes for files and code where they do not expose sensitive content. Do not publish raw text or a manifest that permits source reconstruction. Record amendments and deletion/withdrawal effects; never silently replace a released version. Maintain permission evidence separately under restricted access. Versioning and provenance do not themselves establish rights.
