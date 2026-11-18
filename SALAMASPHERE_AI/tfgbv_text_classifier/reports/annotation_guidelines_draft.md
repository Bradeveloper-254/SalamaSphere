# Draft annotation guidelines for TFGBV research

**Status:** protocol draft for expert and community review. It is not an approved production rubric and no new TFGBV corpus has been collected under it.

## Unit and context

Annotate a message as written, preserving its language and spelling. Label the target, speaker/author role only when known, direction of the act, and whether context is sufficient. Use surrounding thread context only when collection is lawful, necessary, and access controlled. Do not infer identity, gender, intent, consent, or truth from a text fragment alone.

## Multi-label categories

- `non_tfgbv`: no TFGBV behavior in the available content; may still be rude or offensive.
- `gendered_hate`: degrading or hostile content targeting someone based on gender or sex.
- `misogyny`: hostility or contempt toward women/girls because of gender.
- `sexual_harassment`: unwanted sexualized remarks, propositions, or targeting.
- `sexual_coercion`: pressure, manipulation, or threats used to obtain sexual activity or content.
- `unwanted_sexual_content`: unsolicited sexual material or sexualized content directed at a person without consent. Do not ask annotators to open or reproduce explicit material; use a safe metadata label and restricted handling.
- `image_based_abuse`: non-consensual sharing or threatened sharing of intimate images, or coercive use of such images.
- `threats_of_violence`: threatened physical or sexual harm. Record explicitness and immediacy separately; do not predict whether a threat will occur.
- `blackmail_extortion`: demand or pressure backed by a threat to expose, harm, or coerce.
- `cyberstalking`: repeated unwanted digital pursuit, monitoring, or contact. A single isolated message is insufficient without additional evidence.
- `doxxing_privacy_violation`: disclosure or threatened disclosure of private identifying information without consent.
- `impersonation`: deceptive identity use to harass, expose, threaten, or coerce.
- `body_shaming`: degrading remarks about a person's body; add a gendered label only where supported by the content/context.
- `uncertain_context`: context, target, quotation, sarcasm, reclaimed language, or translation is unclear. This flag can accompany a provisional label.

General profanity, political insults, and non-gendered conflict are not automatically TFGBV. Counterspeech, quotation, reporting, support seeking, and discussion of abuse should not be labeled abusive solely because they contain harmful terms.

## Annotation fields

For each item record multi-label decisions; target type; direct/quoted/reporting context; explicitness; repetition if established by authorized context; language/mix; uncertainty reason; annotator confidence; and a short rationale without copying unnecessary personal data. Severity and immediacy should use separately defined scales and must not be combined into a survivor credibility score.

## Process and safety

Use trained Kiswahili, English, Sheng and regional-language annotators, GBV practitioners, and privacy expertise. Pilot with at least three independent annotators per high-risk item, measure per-label agreement, adjudicate disagreements while preserving original votes, and pay lived-experience contributors. Provide content notices, opt-in participation, breaks, workload limits, withdrawal, and referral/support options. Never require annotators to inspect explicit imagery or identify a person in it.

These guidelines require review by local GBV practitioners, linguists, privacy/ethics reviewers, and compensated community advisors before any annotation begins.
