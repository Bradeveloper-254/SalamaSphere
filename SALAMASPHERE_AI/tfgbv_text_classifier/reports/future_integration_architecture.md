# Future SalamaSphere integration architecture (proposal only)

The classifier in this folder is local research code. It is not integrated with Flutter, Django, the wearable, or emergency workflows. Any later integration requires a newly validated TFGBV dataset and product/privacy review.

## Proposed service boundary

If a validated model is eventually approved, expose it behind an authenticated Django service boundary rather than putting model weights or provider keys in Flutter or firmware. A request should contain only user-submitted text needed for the specific review. Enforce authorization, size/rate limits, TLS, request IDs, and strict retention controls. Never place raw text in routine logs, analytics, traces, or crash reports.

Return a versioned response with model version, label scores, uncertainty/abstention, and clear scope warnings. Scores should be calibrated and validated before being described as probabilities. Low confidence, missing context, out-of-domain language, and model errors should produce an explicit `uncertain` response and a human-review path.

## Human-centered safeguards

- Predictions may offer optional assistance to a trained reviewer; they must never determine whether a survivor report is genuine or whether emergency help is sent.
- Do not automatically rank, penalize, report, or deny services to a person from model output.
- Preserve access to the existing SOS and support flow if the service is offline, slow, or unavailable.
- Keep audit records minimal and privacy-preserving; restrict reviewer access and establish retention/deletion policies.
- Communicate limitations and provide correction/appeal mechanisms.

## Operations and versioning

Version model artifacts, preprocessing, threshold, dataset manifest, and evaluation report as one immutable release. Deploy behind a feature flag, shadow-evaluate first, monitor drift and subgroup performance using consented, minimized data, and roll back without affecting emergency functions. Limit model memory/CPU use and keep inference asynchronous if it is not required for immediate assistance.

No production endpoint, mobile integration, or deployment is part of the current project state.
