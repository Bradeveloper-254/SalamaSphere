# TFGBV-specific Kiswahili dataset development plan

## Purpose and boundary

The current JamiiForums corpus is a general offensive-language resource. It cannot validate a TFGBV classifier. A future TFGBV dataset should be purpose-built, sourced under an explicit legal and ethical basis, and annotated for context rather than keyword presence. This plan does not claim that such a dataset has been collected.

## Sourcing and governance

1. Prefer voluntary, informed contributions, licensed public corpora with clear provenance, or carefully reviewed public examples. Do not scrape private conversations, survivor reports, or protected spaces.
2. Obtain local legal and ethics review before collection, especially for sexual content, minors, and personal data. Record the source, consent/legal basis, retention period, and permitted uses for each example.
3. Remove names, phone numbers, handles, URLs, locations, and other direct identifiers before annotation where feasible. Keep any re-identification map separately under restricted access; do not put raw examples in logs or ordinary analytics.
4. Keep a data statement with languages, dialects, source types, time range, sampling method, exclusions, license/permissions, and known gaps.

## Proposed multilabel taxonomy

Annotators may assign multiple labels to one message. `uncertain_context` is an uncertainty flag and can co-occur with a provisional label.

- `non_tfgbv`: not TFGBV; includes general profanity, political insults, and non-gendered conflict.
- `gendered_hate`: attacks or dehumanization targeting a person/group based on gender or sex.
- `misogyny`: hostility, contempt, or degrading claims directed at women/girls as a group or individual because of gender.
- `sexual_harassment`: unwanted sexual remarks, propositions, or sexualized targeting.
- `sexual_coercion`: pressure, threats, or manipulation to obtain sexual activity or content.
- `threats_of_violence`: explicit or credible threatened physical/sexual harm; annotate target and immediacy separately.
- `image_based_abuse`: non-consensual sharing, threatened sharing, or coercive use of intimate images.
- `blackmail_extortion`: demand backed by a threat to expose, harm, or otherwise coerce.
- `cyberstalking`: repeated unwanted digital pursuit, monitoring, or contact; requires context or thread-level evidence.
- `doxxing_privacy_violation`: disclosure or threat to disclose private identifying information without consent.
- `impersonation`: deceptive use of another person's identity to harm, coerce, or expose them.
- `body_shaming`: degrading or harassing comments about a person's body, annotated with gendered targeting when applicable.
- `uncertain_context`: insufficient context, ambiguous target, sarcasm, quotation, reclaimed language, or annotator uncertainty.

For each label, define inclusion/exclusion rules, target, speaker intent when observable, severity, directness, and context requirements. Do not infer intent or survivor identity from text alone.

## Language and context coverage

Plan collection quotas and audits for Kiswahili, English, Sheng, and code-switched/mixed text, including regional and orthographic variation. Preserve original text and a separately versioned normalized view. Include short replies, misspellings, repeated-character forms, quoted content, counterspeech, and non-TFGBV offensive examples. Store thread context only when lawful and necessary, with strict access controls and minimal surrounding turns.

## Annotation protocol

1. Draft the guide with local Kiswahili/Sheng linguists, GBV practitioners, privacy specialists, and people with relevant lived experience who opt in and are compensated.
2. Pilot a diverse sample; revise definitions and add counterexamples before production labeling.
3. Use at least three trained annotators per example for high-risk classes. Annotators label independently before discussion.
4. Track per-label agreement (for example, Krippendorff's alpha or pairwise agreement), prevalence, and disagreement reasons. Do not collapse uncertain cases merely to improve agreement.
5. Resolve disagreements with a trained adjudicator and preserve original votes, adjudicated labels, and rationale in restricted data.
6. Split by source thread/author and time where lawful metadata exists; never place near-duplicate posts from one thread across splits. Keep a separate external-source evaluation set.

## Trauma-informed safeguards

- Provide opt-in participation, content warnings, breaks, workload limits, and a clear pause/withdrawal process.
- Offer access to trained support and avoid assigning annotators repeated graphic content.
- Hide usernames and irrelevant personal details; restrict raw-text access and never expose examples in public logs or dashboards.
- Establish incident escalation, secure storage, deletion schedules, and access audits before annotation begins.

## Release and evaluation gates

Release only after permissions, privacy review, documentation, and a misuse assessment. Consider a controlled-access release if public redistribution is not clearly permitted. Report classwise metrics, calibration where applicable, performance by language/dialect/source, uncertainty, and error analyses with minimized examples. Do not market predictions as proof, triage truth, or grounds to deny assistance. Require human review and survivor-centered appeal paths in any later system.
