# First Model Development Plan completion report

**Report date:** 2026-11-18 (Africa/Nairobi)  
**Repository:** SalamaSphere root checkout, `main` at starting commit `85ded85`; changes are local and uncommitted.  
**Scope limitation:** The separately referenced Flutter repository is not present in this checkout. No remote was fetched, and no deployment or hardware session was available.

## 1. Executive summary

The First Model Development Plan is **not complete**. Research preparation is substantial but remains draft and unapproved. A general Kiswahili offensive-language baseline exists, but it is not a TFGBV detector. Its source permissions are unresolved and the previously used test set is no longer an untouched independent evaluation. There is no authorized TFGBV dataset, annotation, training, or evaluation.

The Django `threat_analysis` code is an experimental rules-based severity workflow, not integration of the ML baseline. Because it can infer and persist a low/medium/high threat level from incident text, this work adds an independent, default-off feature setting for both of its endpoints. Focused and full backend tests passed. Flutter, device hardware, and production behavior remain unverified.

## 2. Stage-by-stage status

| Stage | Original Objective | Status | Completed Tasks | Remaining Tasks | Evidence |
|---|---|---|---|---|---|
| 1. Setup and research preparation | Prepare reproducible, governed TFGBV research | PARTIALLY COMPLETE | Draft protocol, source register/checklist, schema, annotation guide, risk register, roadmap and model card exist; audit completed | Obtain institutional/supervisor, legal/source, privacy and language review; verify licensing; resolve open governance/methodology items; complete reusable experiment tracking and setup details | `SALAMASPHERE_AI/tfgbv_text_classifier/reports/`; `Data/DATA_SOURCES.md`; this audit |
| 2. Data collection and preparation | Establish provenance-safe prepared data | PARTIALLY COMPLETE | Existing baseline cleaner, quality summary and split/error documentation are present; raw/local processed data is not collected by this work | Establish source rights; audit transformations and leakage rigorously; ensure no text leaks to reports; version the dataset and splits; create independent future test set. Do not collect TFGBV text before approvals | `src/inspect_dataset.py`; `reports/dataset_quality_report.csv`; `reports/final_model_evaluation.md`; local CSVs ignored by Git |
| 3. Human annotation | Approve and conduct human annotation | PARTIALLY COMPLETE | Draft rubric, schema, synthetic examples in guide, pilot plan and approval checklist are present | Taxonomy and instructions need qualified review; create/validate annotation tooling and agreement calculation; approve pilot, recruit/train annotators and conduct annotation only after approvals | `reports/annotation_guidelines_draft.md`; `reports/dataset_schema_and_data_dictionary.md`; `reports/pilot_study_plan.md` |
| 4. Train the classifier | Train a valid TFGBV model reproducibly | PARTIALLY COMPLETE | Existing general offensive-language Logistic Regression and Linear SVM pipeline/artifacts and historical results are preserved; inference bundle tests pass | No TFGBV model can be trained until an approved dataset exists; audit reproducibility/metadata and artifact dependencies; future model selection must use approved train/validation data only | `src/train_baseline.py`; `src/train_svm.py`; `reports/model_card.md`; `README.md`; ML test results below |
| 5. Evaluate the classifier | Evaluate model, errors and future TFGBV system | PARTIALLY COMPLETE | Historical baseline metrics and limitations are reported; evaluation guard and inference tests exist | Existing test is previously examined and is descriptive only; create fresh independent held-out TFGBV evaluation after approval; define and approve subgroup, harm, uncertainty and acceptance methods | `reports/final_model_evaluation.md`; `reports/validation_model_comparison.json`; `reports/model_research_roadmap.md` |
| 6. Django integration | Integrate an isolated optional AI service safely | PARTIALLY COMPLETE | Existing authenticated rules-based assessment API audited; introduced an independent default-off switch and tested unavailable behavior | Current service is not the ML model and uses unapproved automatic severity rules; decide approved use/methodology before enabling; no model inference endpoint, model metadata, timeout/resource guard, or API docs for ML integration | `backend/threat_analysis/`; `backend/config/settings.py`; `.env.example`; backend tests |

## 3. Changes made

- `reports/final_project_audit.md` — initial repository inventory, stage gaps, risks and safe work plan, followed by mitigation/test evidence.
- `reports/first_model_development_completion_report.md` — this stage-by-stage evidence and blocker report.
- `.env.example` — documents `EXPERIMENTAL_THREAT_ASSESSMENT_ENABLED=False`.
- `backend/config/settings.py` — reads the experimental assessment switch, defaulting to disabled.
- `backend/threat_analysis/views.py` — returns HTTP 503 from both experimental assessment endpoints while the switch is disabled.
- `backend/threat_analysis/tests.py` — explicitly enables endpoints for existing positive API tests and tests the disabled create endpoint.
- `docs/security_and_data_handling.md` — corrects stale claims about tracked CSVs; clarifies the two tracked text-bearing validation error reports and local processed-split status without reproducing any row content.

No data, model artifact, firmware, production database, Git history, or remote was changed. No data collection or new model training was performed.

## 4. Testing report

| Command | Environment | Result | Notes |
|---|---|---|---|
| `..\.venv\Scripts\python.exe manage.py test threat_analysis --verbosity 2` (first attempted from `backend`) | PowerShell, backend directory | Did not run | The relative path was incorrect. Corrected command below; no test result was inferred from this attempt. |
| `.\.venv\Scripts\python.exe manage.py test threat_analysis --verbosity 2` | `backend/.venv`, Python 3.14.3, local PostgreSQL test DB | PASS: 14 tests, 0 failures, 0 skipped | Initial focused run. A later focused run with the review-endpoint disabled case passed 15 tests; see next row. |
| `.\.venv\Scripts\python.exe manage.py test threat_analysis --verbosity 1` | `backend/.venv`, Python 3.14.3, local PostgreSQL test DB | PASS: 15 tests, 0 failures, 0 skipped | Final focused run after adding disabled review-endpoint coverage. |
| `..\.venv\Scripts\python.exe -m pytest -q` | `SALAMASPHERE_AI/.venv`, Python 3.14.3 | PASS: 10 tests, 0 failures, 0 skipped | ML inference/model loading suite; no test-set evaluation or external service. |
| `.\.venv\Scripts\python.exe manage.py test --verbosity 1` | `backend/.venv`, Python 3.14.3, local PostgreSQL test DB | PASS: 149 tests, 0 failures, 0 skipped; system check: 0 issues | Took 324.684 seconds. Notification timeout/provider error logs were emitted by simulated tests; the suite completed OK. Simulated output explicitly indicated no real SMS/call. |
| `git diff --check` | Root repository | PASS | No whitespace errors. |
| Targeted `git grep -Il -E` scan for common key/private-key patterns in `HEAD`, excluding CSV/model binaries | Root repository | No matches | Heuristic current-tree scan only; not a comprehensive history or dependency scan. |

Flutter analyze/tests were unavailable because the `mobile/` directory is empty and no Flutter checkout is present. No hardware/device tests, dependency vulnerability scan, live API tests, or production tests were run.

## 5. Security and privacy review

| Finding | Severity | Mitigation/status | Remaining risk |
|---|---|---|---|
| Rules-based Django service can automatically assign and persist severity based on incident text/indicators; methodology is not evidenced as approved | High | Both endpoints now default disabled through `EXPERIMENTAL_THREAT_ASSESSMENT_ENABLED=False`; focused tests cover disabled and enabled creation | Setting can be enabled by deployment configuration; do not enable before formal method/use approval. Existing records/results were not migrated or modified. |
| Two validation misclassification CSV reports containing source text are tracked in `HEAD` and history | High | Corrected security documentation and did not print or alter content | Keep access restricted. Removal/history cleanup requires a coordinated separately authorized action; remote history remains unchanged. |
| Underlying forum-post collection permissions are unresolved despite dataset-card license statement | High | Provenance caveat retained; no new use, redistribution, or collection | Obtain source-specific legal/terms review before further use or sharing. |
| Backend `.env` exists locally and is Git-ignored | Unresolved | Contents were not opened or disclosed; targeted scan found no common secret pattern in tracked text | Scan cannot prove absence of secrets, especially in ignored files or history. Keep secret values in managed configuration; rotate any exposed real credential. |
| Test logs include simulated notification/provider diagnostic output | Low | Full test suite ran; no real provider action was initiated by reported simulation output | Review production logging separately to ensure submitted text and sensitive payloads are not logged. |
| Flutter and physical wearable behavior unavailable | Unresolved | No unsupported verification claim made | Client/hardware integration risks remain until separate source/device testing. |

No confirmed live secret was identified by the limited scan. This is not a guarantee that history, dependencies, ignored files or runtime configuration contain none.

## 6. Research approval blockers

The following remain blocked until documented authorization/evidence exists:

- Supervisor and institutional/ethics determination and approval, as applicable.
- Source-by-source permission, platform terms, lawful basis, retention and redistribution decision.
- Approved research scope, taxonomy and annotation rubric with GBV, privacy and Kiswahili/Sheng expertise.
- Approved data storage, access controls, de-identification, deletion and annotator wellbeing procedures.
- Recruitment, data collection, pilot annotation and any use of real TFGBV text.
- TFGBV-specific training/evaluation, publication, or deployment.

No approval, consent, annotation, or TFGBV corpus is represented as obtained.

## 7. Model results

**Generic offensive-language baseline only:** historical reports identify Logistic Regression test accuracy about 70.56%, offensive precision about 87.73%, offensive recall about 45.83%, and macro F1 about 68.42%. The validation-selected Linear SVM reports validation macro F1 79.39% and offensive recall 70.19%; its descriptive test macro F1 is 64.55% and offensive recall 38.78%. The test set has already been used in prior comparisons; these test figures are historical descriptive results and must not guide further tuning.

**TFGBV model:** none trained. There is no approved TFGBV dataset or TFGBV model performance result.

## 8. Django integration status

The existing `threat_analysis` application is a rules/indicator workflow, persists assessments and may update incident severity. It does not call `SALAMASPHERE_AI` or load the general offensive-language artifact. This work added a configuration flag independent from other backend services; default behavior is HTTP 503 for both assessment and review endpoints. Authenticated positive-path behavior remains covered when the flag is explicitly enabled in tests. The full backend suite passed.

No ML inference API, calibrated confidence, timeout-controlled model call, or Flutter-compatible AI result contract was verified. Keep the switch disabled until methodology and intended use are approved.

## 9. Flutter integration status

NOT VERIFIED / unavailable. The root `mobile/` directory is empty, and the separate `SalamaSphere_Flutter` repository was not available as a checkout. No API integration, model, UX messaging, accessibility, privacy handling, feature flag, or Flutter tests could be inspected.

## 10. Existing safety system regression status

The full Django backend suite passed 149 tests, including backend coverage across incidents, devices, evidence, notifications, trusted contacts and emergency notifications. This is software-level regression evidence only. It is not end-to-end service delivery or physical-device evidence.

| Area | Status |
|---|---|
| Incident/SOS backend paths | Backend test suite passed; no live emergency triggered |
| BLE / wearable communication | NOT VERIFIED on hardware |
| Audio recording / wearable transfer / playback | NOT VERIFIED end-to-end |
| Evidence encryption / integrity | Backend tests passed; no independent cryptographic/security audit |
| Trusted contacts | Backend tests passed; no live notification validation |
| SMS / emergency calls | Simulated/mock backend tests only; no real message or call verification |
| Notifications | Backend tests passed; no mobile push/device verification |
| Offline queues/retries | No complete cross-device offline regression run |
| Flutter safety behavior | NOT VERIFIED; source unavailable |

## 11. Completion percentage

These are planning estimates, not measured coverage. The weights reflect delivered, verifiable work against each stage; approval-gated work is not counted complete.

| Area | Estimate |
|---|---:|
| Technical development | 55% |
| Research readiness | 55% |
| TFGBV dataset readiness | 10% |
| Model development | 25% |
| Evaluation | 30% |
| Django integration | 25% |
| Flutter integration | 0% |
| Overall First Model Development Plan | 29% |

Overall is a conservative unweighted average of the seven area estimates, rounded to the nearest whole percent. Low dataset/model completion reflects the absence of approved TFGBV data and model; the existing baseline is only general offensive-language work. Technical development gives credit to existing baseline tooling and this isolated default-off mitigation, but not to unavailable Flutter and hardware integration.

## 12. Remaining tasks, prioritized

- **P0 — Critical safety/security:** Keep experimental assessment disabled. Restrict access to tracked text-bearing CSV reports; determine source rights and data handling; review production configuration/logging and rotate credentials if a real credential is found exposed. Decide a coordinated history remediation plan if required.
- **P1 — Before pilot:** Obtain supervisor/ethics/legal decisions; approve sources and taxonomy; confirm qualified language/GBV reviewers, storage/access/retention/deletion controls, annotator support, and pilot protocol.
- **P2 — Before model evaluation:** Build an approved TFGBV dataset; validate annotation quality and agreement; define grouped leakage-resistant splits and sequester a fresh independent test set; agree on harm-aware metrics and proposed acceptance criteria.
- **P3 — Before integration release:** Access and audit Flutter repository; implement only an approved advisory use behind a feature flag; define API contract, privacy, timeout/rate/resource limits, human review/correction, and graceful unavailability; run full software and device regression suites; obtain deployment authorization.
- **P4 — Future enhancements:** Consider qualified language-specific analysis, calibration/uncertainty and controlled external evaluation only if research results, rights and compute justify them.

## 13. Next recommended milestone

**Milestone: Research governance approval package accepted for a controlled TFGBV annotation pilot.** Complete and record supervisor/institutional determination, source-specific permissions, legal/privacy review, language/GBV expert review of taxonomy and handbook, approved storage/retention/deletion process, annotator safety plan, and pilot sampling/agreement protocol. Until those gates are met, do not collect or annotate TFGBV data and do not enable the Django experimental assessment endpoints.

| `.\\.venv\\Scripts\\python.exe manage.py test threat_analysis --verbosity 1` | `backend/.venv`, Python 3.14.3, local PostgreSQL test DB | PASS: 15 tests, 0 failures, 0 skipped | Final focused run after adding disabled review-endpoint coverage. |

