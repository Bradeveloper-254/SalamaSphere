# TFGBV model research roadmap

**Current state:** the available model is a local Kiswahili general offensive-language baseline. It is not a TFGBV detector, multilingual model, calibrated risk estimate, or production feature. No additional classifier, acoustic distress detector, or risk fusion engine is part of this milestone.

## Stage 0 — stabilize and govern (current)

- Keep text-bearing data local; keep scripts, aggregate reports, and documentation in source control.
- Maintain source/license uncertainty for the JamiiForums-derived dataset; do not redistribute it until rights are reviewed.
- Preserve the existing model as a research baseline, with its warning and score semantics.
- Keep evaluation-only test data out of iterative scripts. The test split has prior exposure, so existing metrics are descriptive only.

## Stage 1 — protocol and data readiness

- Obtain ethics, privacy, source permission, consent, and safety review before collecting new TFGBV material.
- Pilot the annotation draft with Kiswahili, English, Sheng, GBV, privacy, and compensated community experts.
- Define intended-use limits, label inclusion/exclusion criteria, context requirements, and incident response.
- Establish secure access, retention/deletion, source provenance, and annotator wellbeing procedures.

## Stage 2 — curated corpus and baseline evaluation

- Collect only approved, minimized examples under the approved protocol.
- Annotate multilabel behavior with independent votes and adjudication; retain uncertainty and provenance.
- De-duplicate and split by author/thread/time where lawful; reserve a truly untouched external test set.
- Compare transparent baselines and language-specific approaches using validation only; report classwise and language-wise errors, confidence intervals where appropriate, and calibration only for calibrated outputs.

## Stage 3 — human-centered research evaluation

- Conduct privacy and memorization review, subgroup/language analysis, misuse assessment, and practitioner review.
- Test abstention and uncertainty behavior; document where context is insufficient.
- Evaluate whether a model adds value to trained human review without delaying support or increasing harm.
- Use controlled research access until rights and release risks are resolved.

## Stage 4 — separate approval for any product integration

Product integration requires a new review of threat model, consent, data minimization, latency, accessibility, model monitoring, rollback, incident response, and user-facing explanation. Model outputs must never establish credibility, predict survivor behavior, rank service eligibility, or suppress an SOS or support request. A classifier, acoustic model, and any fusion logic require separate evidence and approvals; none is implied by this roadmap.
