# SalamaSphere project audit

**Audit date:** 2026-11-18 (Africa/Nairobi)  
**Repository:** root checkout `main`, HEAD `85ded85` (`review-ready draft package`)  
**Scope:** repository and local working tree available at audit time. No remote repository was fetched.  
**Working tree:** clean at start of audit. No root-level changes detected. The `backend/.env` file exists locally and is ignored by Git; its contents were not read or reported. `backend/db.sqlite3` is also ignored.

## Repository inventory

The current checkout is a single Git repository with `backend/`, `SALAMASPHERE_AI/tfgbv_text_classifier/`, `SalamaSphere_device/`, `wearable/`, `web/`, and an empty `mobile/` directory. Only the root `main` branch and `origin/main` remote-tracking branch are present. There is no nested Git checkout for the separately referenced Flutter repository, and the Flutter source is unavailable here. The backend source, models, tests, and docs are in this checkout; no independently checked out backend repository was found.

The latest five commits are `85ded85`, `4777727`, `9e6a608`, `25c18f7`, and `63fa982`. Two recent commits include tracked text-bearing misclassification CSV paths in the ML reports. Do not expose the row contents. The ignored processed dataset directory exists locally but has no tracked CSV files in the current index. Model artifacts are tracked.

## Task status

| Task | Current Status | Evidence | Remaining Work | Risk |
|---|---|---|---|---|
| Repository/branch/worktree inventory | COMPLETE AND VERIFIED | `git status --short --branch` clean; `git branch -a`; `git log -1`; tracked file inventory | Audit separate Flutter repo if made available | Flutter repo state unknown |
| Stage 1: research preparation | PARTIALLY COMPLETE | Draft protocol, annotation guidance, schema, risk register, ethics checklist, model card and roadmap exist under `SALAMASPHERE_AI/tfgbv_text_classifier/reports/` | Supervisor, ethics, legal, source-rights and language-expert review remain; reproducibility/setup documentation and source evidence need review | No approvals or licensing verification evidenced |
| Stage 2: data preparation | IMPLEMENTED BUT NOT VERIFIED | `src/inspect_dataset.py`, quality summary and ignored local processed directory exist; README documents cleaning and splits | Verify source provenance/rights, inspect pipeline behavior and aggregate reports, leakage and reproducibility; avoid reusing test set for selection | User-generated/source-site text rights unclear; data is offensive-language, not TFGBV |
| Stage 3: human annotation | PARTIALLY COMPLETE | Draft handbook, schema, pilot plan and readiness checklist | No annotation interface/validator or agreement utility found; approvals and qualified reviewers required before pilot | Annotation must remain blocked pending approval |
| Stage 4: classifier training | IMPLEMENTED BUT NOT VERIFIED | Baseline/SVM scripts, serialized artifacts and metrics exist; README identifies task as general offensive-language classification | Audit reproducibility, metadata, serialization/loading, dependency pinning and training records; do not retrain against examined test data | Not a TFGBV model; data-source rights not established |
| Stage 5: evaluation | IMPLEMENTED BUT NOT VERIFIED | Validation comparison, error-analysis and final descriptive reports exist | Verify scripts/reports and document test contamination; establish approved future independent evaluation protocol | Test set has already informed prior comparisons; no TFGBV evaluation data |
| Stage 6: Django integration | PARTIALLY COMPLETE | `backend/threat_analysis/` has authenticated endpoints, serializers, service, persistence, tests and URL routing | Existing code is rules-based severity assessment, not the ML baseline; add independent disable switch and assess severity-writing behavior and privacy | Rules can infer and persist severity from descriptions without approved methodology |
| Flutter integration | NOT STARTED | `mobile/` is empty; no Flutter files found in this checkout | Obtain/access `SalamaSphere_Flutter` checkout; audit integration and feature controls | Cannot verify client behavior or compatibility |
| SOS/BLE/audio/evidence/notifications regression | IMPLEMENTED BUT NOT VERIFIED | Related Django tests, firmware files, BLE protocol and evidence docs exist | Run relevant tests; hardware/device workflows require connected hardware and device test | No hardware verification in repository audit |
| Secret/unsafe logging scan | IMPLEMENTED BUT NOT VERIFIED | Targeted Git content scan for common credential/private-key patterns returned no matches in HEAD (excluding CSV/model artifacts) | Broader history/dependency/security scan not run; ignored local `.env` exists and was not read | Scan is heuristic and not comprehensive |

## AI implementation boundary

The ML directory describes a Kiswahili general offensive/non-offensive classifier trained on `metabloit/offensive-swahili-text`. Its README expressly says it is not a TFGBV detector and not deployed. It reports the test set was previously examined and is descriptive only. No evidence in the repository establishes permissions for underlying JamiiForums comments; the dataset card's uploader-declared MIT label does not establish source-site permissions.

The Django `threat_analysis` app is a separate rules/indicator system. `assess_incident()` searches the incident description for English keywords, produces low/medium/high levels, and `ThreatAssessmentCreateView` persists the result and updates `incident.threat_level`. It does not load the ML artifact, and it is not demonstrated as connected to the Flutter client. This automated severity assignment conflicts with the current research prompt's constraint against unapproved automated severity. A default-off independent feature switch is a safe isolated mitigation to implement and verify locally.

## Initial safe implementation plan

1. Preserve this audit as the pre-change baseline.
2. Add an independently controlled, default-off setting for the experimental threat-assessment endpoints, with a clear unavailable response when disabled.
3. Add focused backend tests for the disabled and enabled paths, and run them if dependencies/environment permit.
4. Create the required completion report with actual test outcomes, clear approval blockers, and no unsupported claims about Flutter or hardware.
5. Do not collect data, train new models, deploy, alter firmware, or rewrite history.

## Post-audit mitigation and verification

The initial safe plan was applied: `EXPERIMENTAL_THREAT_ASSESSMENT_ENABLED` is now configurable and defaults to `False`; both experimental assessment endpoints return HTTP 503 while disabled. Focused tests cover disabled and enabled create behavior. The switch does not alter SOS or incident creation routes. `git diff --check` passed after changes.

The backend focused suite passed 14 tests; the full Django backend suite passed 149 tests with no system-check issues. ML inference tests passed 10 tests. These are local test-environment results and do not establish production, Flutter, device, or human-pilot behavior.

The repository's tracked validation misclassification CSVs were confirmed present in `HEAD`, contrary to the earlier wording in `docs/security_and_data_handling.md`. That documentation has been corrected to state their current tracked status and recommend restricted handling. The files and Git history were not altered.

A final focused rerun after adding disabled review-endpoint coverage passed 15/15 tests (`backend/.venv`, Python 3.14.3). The earlier 14-test focused run and 149-test full suite also passed; the extra assertion was subsequently verified in the focused suite.
