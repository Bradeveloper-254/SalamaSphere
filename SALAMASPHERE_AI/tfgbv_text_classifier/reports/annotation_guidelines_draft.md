# Draft annotation handbook: TFGBV text research

**Status:** Proposed draft for supervisor, ethics, privacy, GBV-practitioner, and language-expert review. It is not an approved production rubric. No pilot or new TFGBV annotation has been conducted. **Version:** 0.2 (pre-review). **Review date:** [to be completed].

This handbook is to be used only after the protocol and source have the required documented approvals. See [research protocol](tfgbv_research_protocol.md), [schema](dataset_schema_and_data_dictionary.md), [pilot plan](pilot_study_plan.md), and [readiness checklist](data_collection_and_ethics_checklist.md).

## Annotator role and responsibilities

Annotators describe evidence present in an approved text sample; they do not determine whether an allegation is true, identify a victim or perpetrator, infer intent beyond textual evidence, assess imminent danger, or provide case triage. Follow the approved handling instructions, minimize copied text in notes, use the uncertainty options, and pause/escalate using the approved safety contact if content causes distress or appears to require a safety response. Do not independently search for a source or contact a person mentioned in a record.

## Unit, context, and decision sequence

The default unit is one approved, privacy-screened text message or post. A conversation/thread may be used only if permissions specifically allow it and the minimum surrounding context is necessary to interpret the unit. Annotate the target unit; use context solely to resolve reference, repetition, quotation, or consent ambiguity. Never assume missing context. Do not retain handles or identity-linking metadata in the annotation workspace.

For every unit: (1) assess context sufficiency; (2) identify whether the text is perpetrating, quoting/reporting, counterspeech/support, or unclear; (3) assign zero or more supported TFGBV labels; (4) assign `non_tfgbv` only when the reviewed context supports no TFGBV label; (5) record language/mix, target type if supported, uncertainty reason, and confidence. `uncertain_insufficient_context` is a record disposition, not a claim that TFGBV did or did not occur. It may accompany provisional labels. Do not force uncertain records into `non_tfgbv`.

## Proposed label set and boundaries

Labels are multi-label: assign each category independently when its definition is met. The set is a proposal requiring expert review, including whether categories should be combined or split. Do not infer the speaker's gender or the target's gender from names, pronouns alone, or stereotypes.

| Label | Apply when | Do not apply solely because |
|---|---|---|
| `non_tfgbv` | Available sufficient context contains no TFGBV behavior; ordinary disagreement or profanity may still be present. | A keyword appears in a quote, report, educational discussion, or counter-speech. |
| `gendered_hate` | Hostility, dehumanization, or exclusion targets a person/group on the basis of gender/sex. | Insult is generic or target basis is not supported. |
| `misogyny` | Content expresses hostility, contempt, or degrading claims toward women/girls as such. It may co-occur with gendered hate. | A woman is criticized without evidence the attack is gender-based. |
| `sexual_harassment` | Unwanted sexualized remarks, propositions, or targeting are directed at a person. | A consensual, mutually framed exchange is evident, or sexual vocabulary alone occurs. |
| `sexual_coercion` | Pressure, manipulation, or threats are used to obtain sexual activity or sexual content. | A request or proposition appears without coercive pressure. |
| `threats` | A communicated threat of physical harm or other violence is present. Record threat type separately; do not predict credibility or imminence. | Anger, profanity, or figurative language lacks a threat. |
| `threats_of_sexual_violence` | A communicated threat of sexual violence is present. Also assign `threats` when its broader definition is met. | Sexualized insult is not a threat of violence. |
| `image_based_abuse` | Intimate image/video is shared, threatened, or used coercively without consent. Use only safe, text-based evidence/metadata; never open media. | The text merely mentions an image or consensual sharing. |
| `nonconsensual_intimate_content` | Text indicates intimate content was distributed or made accessible without consent. Co-assign `image_based_abuse` when abuse use/threat is supported. | The annotator cannot establish consent from available evidence; use uncertainty. |
| `sexual_extortion` | A demand for money, sex, content, or another action is backed by threatened exposure or harm of sexual/intimate content. | Threatened exposure is not linked to a coercive demand; consider `blackmail` or other supported label. |
| `blackmail` | A demand or coercion is backed by a threat to expose, harm, or disclose information. | A threat with no demand or coercive leverage is present. |
| `cyberstalking` | Repeated unwanted digital pursuit, monitoring, or contact is evidenced by approved context. | A single isolated message, absent evidence of repetition. |
| `doxxing` | Private identifying information is disclosed or threatened for exposure without consent. Do not retain the identifying information itself. | Non-identifying public information or consented sharing. |
| `privacy_violation` | A privacy intrusion or disclosure is indicated but does not meet the narrower doxxing definition; specify only with evidence. | Mere reference to private matters without evidence of intrusion/disclosure. |
| `impersonation` | Deceptive use of another identity is evidenced and is used to harass, threaten, expose, or coerce. | An account/person cannot be authenticated from the approved text. |
| `gendered_body_shaming` | Degrading body-related remarks are gendered or sexualized in the available context. | General body criticism without gendered targeting; do not infer from target identity. |
| `unwanted_sexual_content` | Unsolicited sexualized text/content is directed to a person without consent. Do not inspect explicit media. | Sexual content is consensual, general discussion, or only quoted for reporting. |
| `stalking_surveillance` | Non-digital or broader monitoring/pursuit is described; use only where the approved context supports it. | A single observation or ordinary contact. Distinguish from `cyberstalking` where possible. |
| `gender_based_intimidation` | Threatening or coercive conduct aims to silence, exclude, or control a person based on gender, beyond a more specific label. | A more specific label fully describes the conduct and there is no additional supported intimidation. |
| `other_tfgbv` | Clear TFGBV is present but no proposed category fits. Add a brief minimized rationale and flag taxonomy review. | The annotator is unsure whether the conduct is TFGBV; use uncertainty. |
| `uncertain_insufficient_context` | Context, target, meaning, consent, quotation, sarcasm, or language interpretation is insufficient for confident classification. Record reason. | The annotator simply dislikes or finds the content offensive. |

Multiple labels can co-occur only when each definition is independently supported. In particular, broad/narrow label pairs (`threats` + `threats_of_sexual_violence`; `image_based_abuse` + `nonconsensual_intimate_content`; `blackmail` + `sexual_extortion`) may intentionally co-occur. `non_tfgbv` must not co-occur with a confirmed TFGBV label. If a suspected TFGBV act is only quoted or reported, annotate the discourse role and do not label the reporter as perpetrating it.

## Discourse role, target, confidence, and uncertainty

Proposed discourse-role values: `apparently_perpetrating`, `quoting_or_reporting`, `counterspeech_or_support`, `educational_or_news_discussion`, `unclear`. These describe text function, not a verified person's role. Target type: `individual`, `group`, `self`, `unclear`, `not_applicable`; add a gender basis only when explicitly supported. Confidence is an annotator's confidence in this annotation (`high`, `medium`, `low`), not a probability of real-world harm. Low confidence requires an uncertainty reason; it does not automatically invalidate a label.

Use `uncertain_insufficient_context` when reasonable readings differ and the text/context provided cannot resolve them. Choose reason(s): `missing_context`, `ambiguous_target`, `ambiguous_language`, `sarcasm_or_irony`, `quotation_or_report`, `consent_unclear`, `gender_basis_unclear`, `translation_uncertain`, `other`. Never resolve uncertainty by guessing. An adjudicator may preserve uncertainty rather than force consensus.

## Non-TFGBV, exclusion, and borderline rules

General profanity, non-gendered insults, political disagreement, ordinary criticism, consensual sexual communication, and discussion/reporting of abuse are not automatically TFGBV. Exclude records that fail source authorization, contain direct identifiers that cannot safely be minimized, require opening intimate imagery/audio, concern minors or child sexual abuse content unless a separately approved protocol expressly covers them, or cannot be handled within approved safeguards. Mark the exclusion reason in a restricted workflow; do not copy unsafe content into notes.

### Synthetic examples (invented for training; not real messages)

These examples are English-only, deliberately generic, and require local expert adaptation. They are not evidence of Kenyan usage and are not a substitute for native-speaker-reviewed examples.

| Synthetic text | Proposed handling |
|---|---|
| “That plan is foolish.” | `non_tfgbv` if sufficient context; generic criticism. |
| “Women should not be allowed to speak here.” | `gendered_hate`, possibly `misogyny`; basis is explicit. |
| “I will post your private photos unless you send me money.” | `image_based_abuse`, `nonconsensual_intimate_content` only if non-consent is supported, `sexual_extortion`, `blackmail`; uncertainty if image/context/consent status is unclear. Never seek or view the photos. |
| “She wrote, ‘I will hurt you’; I am asking for help.” | `quoting_or_reporting`; do not assign perpetration label to reporter. The quoted threat may be represented as reported content only if schema/protocol permits. |
| “Nice work on the presentation.” | `non_tfgbv` if context sufficient. |

## Language and cultural review requirements

Language labels describe the observed record, not model competence. Proposed coverage is Kiswahili, English, Sheng, Kiswahili-English/English-Kiswahili code-switching, and other mixtures only when specifically justified and reviewable.

| Language/mix | Anticipated challenges and review requirement |
|---|---|
| Kiswahili | Register, regional variation, indirect expression, morphology, spelling variation, pragmatic meaning. Qualified Kiswahili native-speaker review required; disputed or unfamiliar wording goes to language review. |
| English | Kenyan/East African usage, local pragmatic meanings, sarcasm, borrowed terms, and variation from standard written English. Locally experienced English reviewer required for disputed cases. |
| Sheng | Fast-changing vocabulary, locality and peer-group variation, creative spelling, mixed morphology, and high ambiguity outside context. Sheng-qualified native-speaker review required; if unavailable, mark unsupported/uncertain rather than guess. |
| Kiswahili-English code-switch | Meaning may depend on clause-level switching, morphology, and pragmatic context. Review by a bilingual annotator; preserve language mixture and flag uncertain segment. |
| English-Kiswahili code-switch | Same constraints; direction/order is not a distinct competence claim. Review by a bilingual annotator. |
| Other mixture | Include only with documented research justification and qualified reviewer capacity. Otherwise exclude or mark language unsupported under approved rules. |

Do not translate away ambiguity. Preserve the approved original text, record language/mix and any translation as a separate, attributed field if the approved design permits it. Do not normalize text destructively: spelling variants, slang, punctuation, emoji, or repetition may affect meaning. A normalization view must remain separate from source text and be versioned. Sarcasm, indirect threats, reclaimed terms, and slang require context and may merit `uncertain_insufficient_context`. Examples and glosses in all Kenyan languages/varieties require native-speaker and community review before training use.

## Quotation, reclaiming, gender ambiguity, and consent

Distinguish the text's apparent act from its mention of an act. Quotation, reporting, counterspeech, support-seeking, news, and education do not become perpetration labels because they repeat harmful terms. Reclaimed language or consensual banter should not receive an abuse label solely because of wording; if relationship, consent, or discourse context is unavailable, preserve uncertainty. Gender of speaker/target must remain unknown unless the text itself clearly supports the relevant attribute; never infer from a name, profile, or stereotype. A fragment cannot establish consent, truth, or intent.

## Disagreement, adjudication, and quality checks

Annotators label independently before discussion. Record original votes and uncertainty. For disagreements, a trained adjudicator reviews the guideline, available approved context, and minimized rationale; seeks language/GBV expertise where required; records a reason code and whether the result is `resolved`, `retained_uncertain`, `excluded`, or `taxonomy_gap`. No majority vote may override an unsafe or unsupported inference. Preserve pre-adjudication labels for agreement analysis.

Quality checks may include blinded calibration examples, schema validation, missing-field checks, label co-occurrence review, drift checks, and a random double-coded subset. Do not use hidden traps or punitive performance ranking. Report per-label agreement and qualitative disagreement types; aggregate scores do not establish validity. Correct errors through documented versioned amendments. Never put raw text in ordinary logs, issue trackers, or public reports.

## Annotator safety and wellbeing

Before any approved annotation, provide content notices, opt-in participation, a pause/withdrawal route, breaks, workload limits, rotation away from graphic topics, confidential support/referral information, and a named escalation contact. Annotators may skip content without penalty under the approved procedure. Never require viewing intimate images or audio. Training must cover privacy, secure workspaces, no personal-device copies, no external searching, and safe incident handling. The research lead must document support arrangements and incident response before access is granted.
