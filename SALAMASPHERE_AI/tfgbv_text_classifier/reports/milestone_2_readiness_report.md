# Milestone 2 readiness report

**Assessment date:** 18 November 2026 (Africa/Nairobi). **Status:** Documentation preparation complete; external review and approvals remain outstanding.

## Summary

The existing TFGBV research notes were consolidated into a coherent draft protocol package in the established AI research reports directory. Definitions now distinguish confirmed categories, non-TFGBV, discourse role, and insufficient context; source permissions, minimization, annotation quality, pilot boundaries, leakage controls, and future model evaluation are described consistently. All approvals remain unverified/not obtained unless separately evidenced; none was found in the inspected repository materials.

## Documents created or updated

- `tfgbv_research_protocol.md` — rationale, objectives, scope, source and sample rules, annotation/evaluation workflow, approvals, milestones and prohibited activities.
- `annotation_guidelines_draft.md` — operational proposed label definitions, multilabel and uncertainty rules, language review, synthetic examples, adjudication and wellbeing safeguards.
- `dataset_schema_and_data_dictionary.md` — minimized proposed fields, privacy notes, vote separation, versioning and source register template.
- `data_collection_and_ethics_checklist.md` — evidence-based approval/readiness checklist with statuses and owner placeholders.
- `pilot_study_plan.md` — proposed 120-record controlled annotation pilot, overlap, metrics, review and go/no-go criteria; not conducted.
- `dataset_risk_register.md` — structured risks, qualitative ratings, mitigations, residual risks and owners.
- `milestone_2_readiness_report.md` — this report.
- `model_research_roadmap.md` — updated to align future stages with the governance gates and model research scope.
- `tfgbv_dataset_development_plan.md` — updated as a concise entry point to the full protocol package.

## Decisions and proposals

**Established repository facts:** the current model is a general offensive-language baseline and not a TFGBV detector; no TFGBV dataset or pilot results were found in the reviewed reports. Existing final test metrics are historically exposed and descriptive. The repository security document says text-bearing datasets/error reports are sensitive and local copies should remain private.

**Proposals requiring review:** text-only future research; a multilabel taxonomy with explicit non-TFGBV and uncertainty; a 120-record pilot recommendation with two independent votes per item and expanded overlap for a subset/high-risk cases; source-specific approval; qualified local language review; no default severity scale; controlled access and a grouped or source/time split.

## Outstanding approval requirements

- Supervisor and institutional ethics determination/approval.
- Qualified legal/privacy review of applicable law, source terms, copyright, lawful basis, consent and cross-border handling.
- Written per-source permissions for collection, retention, annotation, publication and redistribution.
- Named data controller/custodian, approved storage, access, encryption, retention/deletion and incident response.
- Native/qualified Kiswahili, English, Sheng and bilingual expert review for any claimed coverage.
- GBV practitioner and responsible AI review of taxonomy and misuse controls; annotator wellbeing resources and compensation plan.
- Separate approval to begin any pilot, collect data, train a model, publish/share data, or evaluate product integration.

## Allowed and prohibited activities

Allowed now: documentation review and revision, internal supervisor/ethics preparation, and planning approval questions. Prohibited pending appropriate approvals: actual collection, scraping, downloading or API harvesting; pilot annotation; model training; uploading sensitive data to external providers; model deployment or live workflow integration. The classifier must remain separate from SOS, BLE, audio/evidence, notifications, calls and trusted-contact functions.

## Readiness assessment and exit criteria

**Documentation readiness:** achieved for review. **Research readiness:** not achieved; approvals, source decisions, language capacity, storage and support are unresolved. Milestone 2's preparation exit criteria are met insofar as the requested draft documents now exist and are internally aligned; no external approval or implementation milestone is claimed.

- [x] Existing research materials and security guidance inspected.
- [x] Main protocol and operational handbook prepared.
- [x] Proposed schema and source register template prepared.
- [x] Evidence-based checklist and risk register prepared.
- [x] Pilot designed but not conducted; QC and adjudication specified.
- [x] Language scope and limits documented.
- [x] Future model roadmap aligned with governance and evaluation requirements.
- [x] Approval dependencies and prohibited activities explicit.
- [x] No collection, scraping, download, pilot annotation, or model training performed.
- [x] No application, backend, firmware, BLE, SOS, audio/evidence, notification, or call behavior changed.
- [x] No commit or push performed.
- [ ] Supervisor, institutional, legal, ethics, source, language-expert, and security approvals obtained (outside this milestone; not evidenced).

## Recommended next step

Submit this package to the supervisor and appropriate institutional ethics/privacy reviewers for feedback. Resolve the questions in the protocol and complete the checklist with evidence before authorizing any source or pilot.
