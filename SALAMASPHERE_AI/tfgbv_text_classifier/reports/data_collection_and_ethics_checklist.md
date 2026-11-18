# TFGBV data approval and collection readiness checklist

**Status:** All items start unverified. No approval is represented as obtained. Complete evidence and responsible-role fields before any collection or annotation. See [protocol](tfgbv_research_protocol.md), [source register template](dataset_schema_and_data_dictionary.md#source-register-template), and [risk register](dataset_risk_register.md).

Status values: `NOT STARTED` / `IN PROGRESS` / `NEEDS REVIEW` / `COMPLETED`. Use `COMPLETED` only when the cited evidence is present and reviewed; a checked item without evidence is not complete.

| Section | Checklist item | Required evidence | Status | Responsible role | Notes |
|---|---|---|---|---|---|
| Research approval | Research questions, scope, exclusions and intended use approved | Dated protocol decision | NOT STARTED | Supervisor / research lead: [name] | |
| Research approval | No emergency-response or case-triage use in scope | Signed scope review | NOT STARTED | Supervisor | |
| Institutional/supervisor approval | Institutional ethics pathway determined | Written determination / application reference | NOT STARTED | Research lead | |
| Institutional/supervisor approval | Supervisor and institutional authorization obtained where required | Dated approval | NOT STARTED | Supervisor | |
| Legal and source permissions | Applicable privacy, copyright, platform, research, and cross-border rules reviewed by qualified reviewer | Written review and date | NOT STARTED | Legal/privacy reviewer | |
| Legal and source permissions | Each source separately approved for collection, retention, annotation, publication, redistribution | Completed source register evidence | NOT STARTED | Research lead / source owner | No blanket public-data approval. |
| Data provenance | Origin, chain of custody, source terms and license documented | Source register and versioned evidence | NOT STARTED | Data custodian | |
| Consent and participant considerations | Consent/legal basis and withdrawal path defined where applicable | Approved consent materials or documented basis | NOT STARTED | Ethics lead | |
| Consent and participant considerations | Minors and vulnerable participants handled under explicit approved provisions or excluded | Protocol decision | NOT STARTED | Ethics lead | Default exclude. |
| Public data limitations | Public availability not treated as permission; source terms and expectations reviewed | Source-specific assessment | NOT STARTED | Legal/privacy reviewer | |
| Privacy | Direct identifiers removed before annotation; residual risks assessed | Privacy screening procedure and evidence | NOT STARTED | Privacy lead | |
| Privacy | Re-identification and contextual linkage risks reviewed | Documented assessment | NOT STARTED | Privacy lead | |
| Data minimization | Every field justified; no identifiers or unnecessary context | Approved schema | NOT STARTED | Data custodian | |
| Data minimization | No raw audio/images in text dataset by default | Schema and handling procedure | NOT STARTED | Research lead | |
| Secure storage | Approved storage location, controller, custodian and backup defined | Security approval / system record | NOT STARTED | Security lead | |
| Access control | Least-privilege roles and access review established | Access matrix and audit evidence | NOT STARTED | Data custodian | |
| Encryption | Encryption in transit/at rest and key handling verified | Configuration review; no secrets in repo | NOT STARTED | Security lead | |
| Retention | Retention period, triggers, withdrawal/deletion and backup rules approved | Retention schedule | NOT STARTED | Data controller | Duration unresolved. |
| Deletion | Secure deletion method and deletion evidence process tested | Procedure and test record | NOT STARTED | Data custodian | |
| Annotation safety | Content notices, pause/skip/withdrawal, workload limits and support route defined | Approved wellbeing plan | NOT STARTED | Annotation lead | |
| Annotator training | Rubric, security, privacy and escalation training completed | Materials and completion record | NOT STARTED | Annotation lead | |
| Trauma-informed practice | Qualified support, confidential referral, breaks and rotation available | Named support plan and resource confirmation | NOT STARTED | Research lead | |
| Language expert review | Kiswahili, English, Sheng and code-switch reviewers identified for claimed coverage | Reviewer qualifications and signed review | NOT STARTED | Language lead | Coverage conditional on capacity. |
| Data quality | Sampling frame, inclusion/exclusion and duplicate review approved | Sampling plan and QA plan | NOT STARTED | Research lead | |
| Dataset versioning | Schema, guideline, transformations and provenance versioned | Manifest template and version control plan | NOT STARTED | Data custodian | |
| Leakage prevention | Duplicate, source/thread grouping, split isolation and test access rules approved | Split plan | NOT STARTED | ML research lead | No usernames solely for grouping. |
| Model evaluation | Metrics, uncertainty, subgroup/language analysis and limits defined | Evaluation plan | NOT STARTED | ML research lead | No training in this milestone. |
| Misuse prevention | Misuse cases and prohibited use documented | Misuse assessment / review | NOT STARTED | Responsible AI lead | |
| Publication and sharing | Separate permissions for quotes, aggregate reports, controlled access and redistribution | Publication/release review | NOT STARTED | Research lead / legal reviewer | |
| Incident response | Breach, accidental exposure, distress, urgent content and escalation path defined | Contact tree and response procedure | NOT STARTED | Security / ethics leads | |

## Stop conditions

Do not collect or annotate if any required approval is pending, a source's rights are unclear, storage/access is unapproved, privacy screening cannot remove identifiers, annotator support is unavailable, a language cannot be competently reviewed, or an incident/safeguard failure remains unresolved. This checklist is a planning artifact; no data collection or annotation has been performed.
