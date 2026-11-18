# Proposed controlled TFGBV annotation pilot

**Status:** Planning recommendation only. Pilot has not been conducted; no data collection or annotation is authorized by this plan. **Version:** 0.1. See [protocol](tfgbv_research_protocol.md), [handbook](annotation_guidelines_draft.md), and [schema](dataset_schema_and_data_dictionary.md).

## Purpose and objectives

The pilot will test whether label definitions are understandable, whether taxonomy boundaries are too broad/narrow, whether annotators distinguish categories reliably, whether proposed language coverage is feasible, whether uncertainty options help, whether workload is manageable, whether privacy safeguards function, and whether adjudication is usable. It is a method-development exercise, not a prevalence study, model benchmark, or claim about TFGBV frequency.

## Proposed size and sampling

**Planning recommendation:** 120 eligible, privacy-screened text records from one or more specifically approved sources. This size is a practical starting point to expose workflow problems across categories and language mixtures; it is not a power calculation, prevalence estimate, or scientifically established minimum. Supervisor and ethics review must approve or revise it before any pilot.

Use a documented, permitted sampling frame and stratified purposive coverage of available language mixtures, clear/ambiguous cases, likely label families, and non-TFGBV controls. Do not fabricate balance or infer prevalence from enriched sampling. Include no real victim content from private or leaked sources. Avoid selecting identifiable people or using usernames as sampling units. Exact language/category quotas remain unresolved until approved sources and reviewer capacity are known.

## Language and category coverage

Proposed coverage includes Kiswahili, English, Sheng, and both directions of Kiswahili-English code-switching. Coverage of each language is conditional on qualified reviewer capacity; other mixtures require written justification. Aim to exercise the proposed label boundaries and `non_tfgbv`/`uncertain_insufficient_context`, but rare or unsafe categories must not be artificially sourced. The taxonomy and examples need native-speaker, Sheng-qualified, GBV, privacy, and supervisor review before pilot use.

## Personnel and training

Proposed roles: research lead, privacy screener/data custodian, at least two trained annotators per record, adjudicator, and on-call qualified language/GBV reviewer. Roles may overlap only if independence is preserved and conflict recorded. Annotators need language competence for assigned items and trauma-informed orientation. Training covers protocol boundaries, label definitions, uncertainty, source restrictions, privacy, secure workspace, escalation, opt-out, breaks, and non-punitive quality review. Lived-experience advisors, if engaged, must be compensated and may decline exposure.

Before independent pilot coding, use a small approved calibration set that is not counted in pilot metrics; discuss disagreements, clarify instructions, and freeze a versioned handbook. No actual calibration data may be assembled before approval.

## Independent annotation and overlap

Proposed design: two independent annotators for all 120 records; third independent annotation for a proposed 25% stratified subset and all high-risk/uncertain records where safe and approved. Annotators do not see each other's labels before submission. If the sample is too burdensome, reduce size or overlap only with documented methodological justification; do not remove overlap from priority labels without review. Record skips and missing annotations without penalty and analyze missingness.

## Agreement and adjudication

Report per-label raw agreement and confusion matrices; Cohen's kappa for two annotators and an appropriate categorical decision; Krippendorff's alpha for suitable multi-annotator/missing-data cases; label prevalence; agreement on context sufficiency and uncertainty; and qualitative disagreement themes. Rare labels and prevalence imbalance can make chance-corrected metrics unstable; no single threshold proves validity. Confidence intervals may be wide at pilot size. Do not report an aggregate score alone.

**Proposed review trigger:** for sufficiently represented priority labels, kappa/alpha of at least 0.67 is a discussion threshold for considering a next research step, not a universal standard and not automatic approval. Any poorly represented label, high-impact disagreement, privacy/safety incident, language gap, or persistent uncertainty requires review regardless of aggregate scores. Adjudicator resolves only supported cases; may retain uncertainty, identify taxonomy gap, or exclude. Preserve pre-adjudication votes and record rationale without duplicating sensitive text.

## Privacy safeguard exercise

Before access, test the approved minimization and pseudonymization workflow using synthetic data only. During any later authorized pilot, verify role-based access, encryption, audit events, no text in logs/exports, redaction, backup/deletion procedures, and incident escalation. Stop access and follow the approved response if a safeguard fails. This plan itself includes only synthetic examples and did not exercise a live data system.

## Pilot review and go/no-go

Proceed to a proposal for a larger study only if: all required approvals remain valid; no unresolved critical privacy/safety event; source permissions cover each actual use; annotator support and language expertise were adequate; the schema and retention/deletion process worked; label definitions and uncertainty are usable or revised; workload is acceptable; disagreement is understood; and a supervisor/research team signs a documented decision. A no-go or revise decision is acceptable. Pilot data must not be repurposed for model training unless specifically authorized and consent/permissions cover that use.

## Reporting template

1. Protocol, source, schema, and handbook versions; approval evidence references.
2. Planned and completed sample counts; exclusion and missing-annotation counts by safe aggregate.
3. Language/source/category coverage, with small-cell disclosure review.
4. Training and annotator workload; opt-outs, pauses, and safety incidents (aggregate, privacy protected).
5. Per-label agreement, uncertainty/context agreement, confusion matrices, prevalence, metric limitations.
6. Disagreement themes and adjudication outcomes; taxonomy/guideline changes.
7. Privacy/security safeguard review, retention/deletion evidence, incidents and resolution.
8. Limitations, go/no-go decision, named reviewer roles, date, and next approval required.

No results should be filled in until an approved pilot actually occurs. No collection, scraping, downloading, model training, or pilot annotation occurred during this milestone.
