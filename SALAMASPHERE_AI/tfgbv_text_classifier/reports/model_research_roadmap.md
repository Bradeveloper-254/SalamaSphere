# TFGBV research roadmap

**Status:** Future research plan; no TFGBV data collection, model training, or deployment is authorized by this roadmap. See [research protocol](tfgbv_research_protocol.md), [pilot plan](pilot_study_plan.md), and [readiness report](milestone_2_readiness_report.md).

## Current state

The available model is a local Kiswahili general offensive-language baseline. It is not a TFGBV detector, multilingual model, calibrated risk estimate, or production feature. Its existing test split was previously examined; reported metrics are descriptive, not an untouched independent estimate. See the [model card](model_card.md) and [final evaluation](final_model_evaluation.md). No TFGBV-specific corpus or pilot results are documented.

## Stage 0 — protocol and governance preparation (current milestone)

- Maintain the research protocol, operational annotation draft, schema, source register, checklist, pilot plan, and risk register as versioned review documents.
- Keep sensitive text, transcripts, incident evidence, and text-bearing error samples private; do not add sensitive data to public Git.
- Do not collect, scrape, download, annotate, or train during this stage.
- Keep all research outside SOS and emergency-response functionality.

## Stage 1 — independent review and authorization (future, conditional)

- Obtain supervisor/institutional ethics determination and applicable legal/privacy review.
- Approve each source and each intended use in the source register; resolve provenance, terms, consent, copyright, privacy and retention.
- Confirm secure storage, access, encryption, deletion and incident response.
- Review taxonomy and language coverage with GBV practitioners and qualified Kiswahili, English, Sheng and bilingual experts.
- Confirm annotator training, wellbeing support, workload limits and resources.

## Stage 2 — controlled annotation pilot (future, conditional)

- If separately approved, execute the proposed small pilot under the protocol and report agreement, uncertainty, workload, language coverage, privacy safeguard performance and adjudication themes.
- Revise taxonomy/guidelines transparently and make a documented go/no-go decision. Do not treat pilot results as prevalence estimates or model validation.

## Stage 3 — TFGBV-specific model research (future, separate approval)

Only after approved data and a formal go decision, consider multilabel classification and compare transparent baselines (majority/prior, TF-IDF with linear logistic or SVM) before multilingual transformer candidates such as XLM-R where justified. Evaluate language-specific and code-switch performance, per-label false positives/negatives, calibration, uncertainty/abstention, reviewer-facing explanations, subgroup/source differences, privacy/memorization, compute, model size, inference latency and offline feasibility. Keep the final test isolated from iterative model selection. Explainability supports review; it does not prove causal reasoning or correctness.

## Stage 4 — human-centered and misuse evaluation (future, separate approval)

Assess whether a model adds value to trained human review without increasing harm. Evaluate false-positive and false-negative consequences, subgroup gaps, over-reliance, misuse, privacy, uncertainty and withdrawal/appeal paths. Use controlled access until rights and release risks are resolved. Do not use model output to establish credibility, predict survivor behavior, rank service eligibility, or suppress support.

## Stage 5 — separate product review (not authorized)

Any product integration requires its own evidence and approval covering consent, threat model, data minimization, latency, accessibility, human oversight, monitoring, rollback, incident handling and user-facing explanation. Research outputs must never block, delay, cancel, downgrade or override SOS activation, notification delivery, evidence recording, emergency calls, trusted contacts or access to help. No integration work is part of this roadmap's current milestone.
