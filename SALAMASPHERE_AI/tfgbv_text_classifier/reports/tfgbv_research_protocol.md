# SalamaSphere TFGBV Text Dataset Research Protocol

**Status:** Proposed protocol for review; no ethics, institutional, legal, source, or participant approval is represented as obtained. **Version:** 0.1. **Review date:** [to be completed]. **Principal researcher / supervisor:** [placeholder]. **Protocol identifier:** [placeholder].

This protocol defines preparation for a future text-only research dataset on technology-facilitated gender-based violence (TFGBV). It does not authorize collection, annotation, model training, deployment, or integration. The current general offensive-language baseline described in the [AI project README](../README.md), [model card](model_card.md), and [evaluation report](final_model_evaluation.md) is not a TFGBV detector.

## 1. Title, background, and problem

**Title:** *Preparing a governed, multilingual text annotation resource for research on technology-facilitated gender-based violence in Kenya: protocol and controlled pilot plan.*

Digital communication can be used to threaten, harass, coerce, expose, impersonate, surveil, or otherwise target people in gendered ways. Research requires labels that distinguish such behavior from general offensiveness, reporting, counterspeech, consensual communication, and ambiguous fragments. The repository's current Kiswahili offensive-language baseline uses broad offensive/non-offensive labels; its previous test split is historically exposed and its results are descriptive. It cannot validate TFGBV recognition or support emergency decisions. There is currently no TFGBV dataset or pilot result documented here.

**Problem statement:** There is no review-ready, locally evaluated, permissioned TFGBV text corpus or annotation protocol in this project. Scattered plans do not yet specify operational source approval, label boundaries, uncertainty, data minimization, annotator protections, or an evaluation design.

## 2. Objectives and research questions

**Preparation objective:** establish a reviewable method and governance gates for a small future annotation pilot, without collecting data during this milestone.

Proposed research questions, subject to supervisor refinement:

1. Can trained annotators apply a reviewed multilabel taxonomy consistently to eligible, privacy-screened text examples?
2. Which label distinctions and context requirements create persistent disagreement?
3. Can the proposed sampling and safeguards represent the planned language mixtures without claiming language competence from inclusion alone?
4. After an approved pilot and separate decision, what baseline methods merit investigation, and what language-, source-, and class-specific limitations remain?

## 3. Decisions, proposals, unknowns, and scope

| Type | Current position |
|---|---|
| Existing documented fact | The existing model is a general Kiswahili offensive-language baseline, not a TFGBV system; no new TFGBV collection or pilot result is documented. The current classifier and evaluation artifacts are outside this protocol's scope. |
| Proposed for review | Text-only pilot; proposed taxonomy and schema in this report set; initial pilot size of 120 eligible records; at least two independent annotations per record; third review for disagreements and a planned subset. |
| Unresolved | Institution and ethics route, responsible data controller, legal basis, approved sources, consent/withdrawal design, secure storage location, retention duration, funding/support resources, exact language quotas, and intended future release/access model. |
| Not obtained / not authorized | Ethics, institutional, legal, source, participant, and language-expert approvals are not claimed. No collection, scraping, downloading, pilot annotation, TFGBV model training, production integration, or AI use in SOS is authorized by this document. |

This is text-only research preparation. It excludes audio, images, transcripts generated from incident recordings, private messages, leaked content, intimate images, personal identifiers, minors, case triage, and direct participant recruitment until a separate protocol explicitly evaluates and authorizes any such activity. No model output may affect SOS activation, evidence, alerts, calls, trusted contacts, or access to assistance.

## 4. Population, setting, and language scope

The future research population is eligible text records from sources specifically approved for the research question, source-by-source. The research does not infer a writer's or target's identity, gender, location, or lived experience from text. The Kenya/East Africa context is a motivation for local review, not a claim that a convenience sample represents the population.

Proposed language coverage: Kiswahili; English; Sheng; Kiswahili-English and English-Kiswahili code-switching; and other mixtures only with documented justification and reviewer capacity. For each, coverage will be reported as observed sample composition, not model ability. Native or qualified local language experts must review the rubric, examples, translation/glosses, and ambiguous cases. Sheng and mixed forms require explicit expertise; unsupported cases remain uncertain or are excluded under approved rules. Risks include dialect and class bias, evolving slang, spelling diversity, indirect expressions, sarcasm, and uneven source representation.

## 5. Source strategy and approval framework

No source is pre-approved. Candidate source types for evaluation (not collection authorization) are voluntary contributions under a reviewed consent process, research corpora with verifiable provenance and compatible permissions, and selected public material only after terms, rights, privacy, and participant risk review. Public availability is not blanket permission. Do not propose private messages, restricted groups, leaked content, intimate images, survivor case files, or scraped platform content as routine sources.

Before sampling, the research lead completes one source register entry per source and documents: legitimacy, provenance, source terms, copyright/license, privacy and consent/legal basis, identification risk, sensitivity, collection method, research suitability and bias, storage, retention/deletion, annotation, publication, redistribution permissions, and decision owner/date. Unresolved rights or safety questions mean source is excluded pending review. The reusable template is in [data dictionary](dataset_schema_and_data_dictionary.md#source-register-template).

## 6. Inclusion, exclusion, sampling

**Proposed inclusion:** text-only item; source specifically approved; permission and provenance documented; within the declared time/source/language frame; sufficient safe text or permitted minimal context to annotate; direct identifiers removed or transformed before annotator access; and handling consistent with the approved protocol.

**Proposed exclusion:** unapproved or unverifiable source; private/restricted/leaked material; minors or child sexual abuse material without explicit separate authorization (default exclude); intimate images/audio or content requiring opening media; direct identifiers that cannot be minimized; source terms/license unclear; duplicate that adds no distinct information; content outside supported languages/reviewer capacity; or risk exceeding safeguards. Record an exclusion reason without copying the sensitive content.

After source approval, use a documented sampling frame and reproducible random or stratified selection where permitted. Aim for coverage across approved source types, proposed language mixtures, and taxonomy-relevant cases without fabricating prevalence or oversampling identifiable individuals. Any enriched sampling changes prevalence interpretation and must be recorded. No quota or sample is authorized before review. Preserve source-level provenance references separately from the minimized annotation table where needed.

## 7. Proposed annotation and quality workflow

1. Research lead selects only from approved sources and records provenance.
2. Authorized privacy screener minimizes text and marks media/identifier exclusions before annotation.
3. Trained annotators complete safety and rubric training, then an approved calibration exercise.
4. Annotators independently label a planned overlapping subset and all pilot items if feasible; no discussion before first-pass submission.
5. Calculate per-label agreement, confusion matrices, uncertainty/context-sufficiency agreement, and qualitative disagreement reasons.
6. A trained adjudicator reviews disagreements, requests qualified language/GBV input as necessary, and can retain uncertainty or exclude a record.
7. Revise taxonomy and handbook with versioned rationale; rerun calibration on newly approved material if changes are material.
8. Conduct a pilot retrospective and formal go/no-go review. Only a separate documented approval permits any larger study.

The operational details and proposed size are in [pilot study plan](pilot_study_plan.md); annotation decisions are in [handbook](annotation_guidelines_draft.md). Cohen's kappa is suitable for two annotators on a categorical item where assumptions fit; Krippendorff's alpha can accommodate multiple annotators and missingness for appropriate measurement levels. Both can be unstable with rare labels and prevalence imbalance; neither proves validity. Report raw/per-category agreement, uncertainty agreement, confusion matrices, prevalence, confidence intervals where feasible, and qualitative error analysis. Proposed pilot threshold: alpha or kappa at least 0.67 for priority labels as a discussion trigger, not universal proof or automatic authorization; require review of low-prevalence labels and all safety-critical ambiguities.

## 8. Proposed schema, privacy, and security

Use a random record identifier; do not use source usernames or account IDs as record IDs. Do not include names, phone numbers, email addresses, exact addresses, handles, or unnecessary personal data. Keep raw audio and images out of the text dataset by default. The proposed field dictionary, allowed values, examples, privacy notes, versioning, and source register template are in [dataset schema and data dictionary](dataset_schema_and_data_dictionary.md).

Before future collection, name the data controller/custodian, approved storage, access roles, encryption method, audit process, retention period, deletion method, backups, incident response, and any processors or transfers. Apply least privilege; separate provenance linkage from text and annotations; never place raw text in logs, public issue trackers, or reports. The existing repository guidance says text-bearing files and incident evidence are private, and notes prior tracked data cleanup; see [security and data handling](../../../docs/security_and_data_handling.md). This protocol does not change that guidance or authorize adding data to Git.

## 9. Retention and deletion

Retention duration is unresolved and must be approved per source and institution before access. The approval record must define retention start/end events, withdrawal handling where applicable, secure deletion for working copies/backups, legal holds, and deletion evidence. Retain only the minimum provenance needed to audit permissions and reproducibility; avoid keeping a re-identification key unless necessary and approved. Do not commit sensitive data. Review `.gitignore` and staged changes before any future data-related change.

## 10. Ethical risks and researcher wellbeing

Risks include privacy exposure, re-identification, retraumatization, retaliation, false attribution, biased labels, uneven language representation, surveillance/censorship misuse, and mistaken reliance on a classifier. Controls include source authorization, minimization, uncertainty, controlled access, no identity inference, content warnings, opt-in annotation, skip/pause/withdrawal routes, workload limits, breaks, rotation, confidential support, and an incident contact. Lived-experience advisors, if involved, must be compensated, informed, and free to decline; their involvement is not presumed. No annotator should inspect intimate media.

## 11. Evaluation, splits, and leakage control

Evaluation is a future research stage only. First report annotation consistency and dataset limitations; model evaluation only follows approved data and a separate research decision. A future model comparison may include majority/prior baselines, TF-IDF with linear logistic or SVM models, then multilingual transformers (e.g., XLM-R) only if justified by sample size, licenses, compute, and language review. Assess multilabel per-class precision/recall/F1, macro and micro summaries, calibration only after calibration procedure, abstention/uncertainty, language/mix/source groups, false positives/negatives, confidence intervals, model size, inference latency, and offline feasibility. Qualitative review must minimize reproduced text.

Before splitting, perform exact and normalized duplicate checks, plus cautious near-duplicate review within protected workspace. Group by source, thread/conversation, and author only where lawful and ethically available. Do not collect usernames solely to group splits. If group identifiers cannot be retained, group by permitted source/thread identifiers before minimization, then discard identifiers and document residual leakage risk; alternatively use source- and time-held-out evaluation. Use stratification only where feasible without splitting groups. Keep a final test set isolated; do not use it for iterative choices. Annotator notes/rationales stay out of model inputs. When grouping data cannot be retained, use a documented time/source split and state its limitations rather than inventing identity metadata.

## 12. Responsible AI and misuse prevention

This is not a safety classifier, credibility assessor, emergency prioritizer, or moderation authority. Future research must assess false-positive harms, false negatives, language performance gaps, privacy/memorization, calibration, uncertainty, and misuse. Any human-review study requires separate approval. A future model must not block, delay, cancel, downgrade, or override SOS activation, emergency notifications, evidence recording, or access to help. No model will be added to the live workflow under this protocol.

## 13. Milestones and exit criteria

| Stage | Deliverable | Exit criteria |
|---|---|---|
| M2 preparation (this work) | Protocol, handbook, schema, checklist, pilot design, risk register, readiness report | Internally consistent drafts exist; no collection/training/integration performed; approval dependencies are explicit. |
| M3 review and authorization | Signed institutional/ethics/source/legal/security decisions; resolved protocol | Named approvals and evidence logged; source register decisions complete; language and wellbeing capacity confirmed; secure environment ready. |
| M4 controlled pilot (future, conditional) | Pilot labels, agreement and retrospective report | Only approved sources used; quality, safety, privacy, and workload review complete; go/no-go signed; no unresolved critical incident. |
| M5 research decision (future) | Revised protocol and decision on expanded study/model research | Taxonomy and language coverage defensible; risk controls effective; separate approval to proceed; test strategy and resources approved. |

## 14. Risk controls and unresolved questions

The [risk register](dataset_risk_register.md) tracks proposed controls, owners, and review status. Key unresolved decisions for supervisor/research team: (a) research questions and intended contribution; (b) institutional ethics pathway and data controller; (c) applicable legal review and source-by-source permissions; (d) whether participant contributions are contemplated and withdrawal mechanics; (e) sources and lawful sampling frame; (f) supported languages and available qualified reviewers; (g) approved storage, access, encryption, incident handling, retention and deletion; (h) resourcing for annotator support and compensation; (i) final taxonomy and whether severity/directness fields are necessary; (j) future access/publication permissions; and (k) who can authorize transition from pilot to expanded work.

## 15. Current authorization boundary

Permitted now: edit/review documentation, seek internal review, identify candidate approval questions, and plan governance. Prohibited until applicable documented approvals: collect, scrape, download, harvest, receive, or annotate actual TFGBV data; contact participants or sources; download real victim content; train a TFGBV model; upload sensitive data to an external provider; deploy or integrate any AI; or alter product, backend, mobile, firmware, BLE, audio/evidence, SOS, alert, or trusted-contact behavior. No such activity was performed for this milestone.
