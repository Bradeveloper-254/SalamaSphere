# TFGBV data collection and ethics checklist

**Gate:** do not collect or annotate new sensitive messages until an accountable research lead has completed the applicable approvals and documented the decisions below.

## Purpose, authority, and consent

- [ ] Define research questions, intended use, excluded uses, and why each data field is necessary.
- [ ] Identify the data controller, custodians, processors, access roles, and incident contact.
- [ ] Review applicable ethics/IRB, privacy, data protection, platform terms, copyright, and cross-border transfer requirements with qualified counsel/reviewers.
- [ ] Document source-specific permissions and lawful basis. Do not infer redistribution rights from an uploader's dataset license.
- [ ] Obtain informed consent when required and provide withdrawal and deletion pathways.
- [ ] Exclude private groups, direct messages, restricted content, and minors unless a separately reviewed protocol explicitly permits it.

## Minimization and safeguards

- [ ] Minimize collection; avoid handles, phone numbers, location, images, and unnecessary thread history.
- [ ] Separate identifiers from annotations, pseudonymize promptly, and protect any re-identification key separately.
- [ ] Set encryption, least-privilege access, audit logging, retention periods, secure deletion, breach response, and backup rules before collection.
- [ ] Establish safe handling for threats, intimate imagery, child sexual content, doxxing, and other urgent/high-risk material. Annotators must not open explicit imagery.
- [ ] Complete a misuse assessment covering surveillance, censorship, retaliation, profiling, and false accusations.

## Annotation and evaluation

- [ ] Approve the annotation rubric with local language and GBV expertise and compensated lived-experience advisors.
- [ ] Provide trauma-informed training, content notices, breaks, workload limits, opt-out, support, and fair compensation.
- [ ] Audit sampling coverage across Kiswahili, English, Sheng, code-switching, dialect, spelling, source, and time without exposing identities.
- [ ] Track provenance, label definitions, annotator disagreement, adjudication, and dataset versions.
- [ ] Split by author/thread and time when lawful metadata allows; detect duplicates across every split.
- [ ] Keep a separately sourced external evaluation set and prevent test-set use for model or threshold tuning.
- [ ] Evaluate false negatives, false positives, calibration if probabilities are used, subgroup/language performance, and uncertainty.
- [ ] Require human review and ensure model output never denies services or determines the truth of an allegation.

## Release decision

- [ ] Review privacy leakage, memorization, licensing, documentation, and residual re-identification risk.
- [ ] Prefer aggregate reports or controlled access when public release is not clearly safe and authorized.
- [ ] Publish a data statement, limitations, intended-use restrictions, version, and contact for removal requests.
- [ ] Obtain documented approval from the research, ethics/privacy, and security owners before release.
