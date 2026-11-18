# Proposed TFGBV research risk register

**Status:** Initial planning register; owners and likelihood ratings require project review. No approval or risk acceptance is implied. Review before any authorized collection, before pilot access, after incidents, and before publication. See [protocol](tfgbv_research_protocol.md) and [readiness checklist](data_collection_and_ethics_checklist.md).

Likelihood and impact use `Low / Medium / High`; risk level is an initial qualitative planning estimate, not a measured value. Residual risk is the expected remaining exposure after proposed controls and must be reviewed.

| Risk | Description | Likelihood | Impact | Level | Mitigation | Residual risk | Owner placeholder | Review status |
|---|---|---:|---:|---:|---|---|---|---|
| Privacy leakage | Text or metadata exposes a victim, annotator, or contributor. | Medium | High | High | Minimize/redact before annotation; restricted storage; no text in logs, exports, or public reports; audit access. | Medium | Privacy lead: [name] | NEEDS REVIEW |
| Re-identification | Combination of wording, time, source, and context identifies a person. | Medium | High | High | Remove direct identifiers; coarsen dates; assess contextual linkage; controlled access; suppress small cells. | Medium | Privacy lead | NEEDS REVIEW |
| Unauthorized collection | Collection occurs before approval or outside approved scope. | Low | High | High | Explicit gate; source register; role training; no collection during M2; audit methods and access. | Low | Research lead | NEEDS REVIEW |
| Copyright/licensing | Dataset license does not grant rights in underlying posts or text. | Medium | High | High | Source-specific legal review; record rights by use; withhold publication/redistribution absent evidence. | Medium | Legal reviewer | NEEDS REVIEW |
| Source terms violation | Collection or retention conflicts with platform/source terms. | Medium | High | High | Review current terms and collection method before approval; reject unclear sources. | Low/Medium | Legal reviewer | NEEDS REVIEW |
| Sensitive content exposure | Threats, intimate content, doxxing, or graphic descriptions harm annotators or leak. | Medium | High | High | Text-only minimization; no media opening; warnings, skip/pause, access controls, escalation. | Medium | Annotation lead | NEEDS REVIEW |
| Annotator trauma | Repeated exposure causes distress or secondary trauma. | Medium | High | High | Opt-in, workload caps, rotation, breaks, support, withdrawal without penalty, incident response. | Medium | Wellbeing lead | NEEDS REVIEW |
| Language/dialect bias | Slang, Sheng, dialect, code-switching, or spelling variation is mislabeled. | High | Medium | High | Qualified local reviewers; uncertainty path; report coverage and errors; exclude unsupported language. | Medium/High | Language lead | NEEDS REVIEW |
| Label bias | Taxonomy reflects stereotypes or treats reporting/reclaimed terms as abuse. | Medium | High | High | Community/GBV review; explicit discourse roles; independent annotation; audit disagreements. | Medium | Responsible AI lead | NEEDS REVIEW |
| Dataset imbalance | Rare labels or language groups are poorly represented. | High | Medium | High | Document sampling; report counts/uncertainty; avoid unsupported generalization; no fabricated balance. | Medium | Research lead | NEEDS REVIEW |
| Source bias | Sources overrepresent particular platforms, communities, or communication styles. | High | Medium | High | Source diversity review; document selection mechanism; evaluate by source; constrain claims. | Medium/High | Research lead | NEEDS REVIEW |
| Data leakage | Duplicate/related records cross train/validation/test or notes reveal labels. | Medium | High | High | Exact/normalized/near duplicate checks; group by permitted source/thread; isolate test; exclude notes. | Low/Medium | ML lead | NEEDS REVIEW |
| Duplicate/near-duplicate content | Reposts inflate agreement or evaluation results. | Medium | Medium | Medium | Deduplication under protected workspace; record method/version; manual review without retaining identities. | Low | Data custodian | NEEDS REVIEW |
| False positives | Future model labels benign, quoted, or consensual text as abuse. | Medium | High | High | Human review; classwise analysis; uncertainty; never automate sanctions or service decisions. | Medium | ML lead | NEEDS REVIEW |
| False negatives | Future model misses abuse, particularly indirect or code-switched cases. | High | High | High | Evaluate recall and language groups; abstain on uncertainty; do not use to deny assistance. | Medium/High | ML lead | NEEDS REVIEW |
| Model misuse | Research model is repurposed for surveillance, censorship, profiling, or retaliation. | Medium | High | High | Controlled access; intended-use limits; misuse review; do not release sensitive examples/model without approval. | Medium | Responsible AI lead | NEEDS REVIEW |
| Over-reliance on AI | Staff treat output as truth, credibility, or risk score. | Medium | High | High | No emergency integration; clear model card; human review; training and product gate. | Low/Medium | Product safety lead | NEEDS REVIEW |
| Emergency workflow interference | AI blocks, delays, cancels, downgrades SOS, evidence, or alerts. | Low | Critical | High | Keep research separate; prohibit integration in this milestone; separate future safety approval and tests. | Low | Product owner | NEEDS REVIEW |
| Security compromise | Unauthorized access, key loss, or breach exposes sensitive text. | Medium | High | High | Approved encrypted storage; least privilege; key management; logs/audits; incident plan. | Medium | Security lead | NEEDS REVIEW |
| Public repository exposure | Sensitive data or identifiers are committed or published. | Medium | High | High | Keep data out of Git; review `.gitignore` and staged diffs; private storage; secret/data scanning per policy. | Low/Medium | Repository maintainer | NEEDS REVIEW |
| Incorrect capability claims | General offensive baseline is presented as TFGBV detector or supported language capability. | Medium | High | High | Consistent disclaimers; distinguish proposed scope from validated performance; review publication language. | Low | Research lead | NEEDS REVIEW |
| Consent/withdrawal failure | Contribution is used beyond consent or cannot be withdrawn as promised. | Low/Medium | High | High | Approved consent language, data lineage, withdrawal mechanism, retention/deletion tracking. | Medium | Ethics lead | NEEDS REVIEW |

## Review record

| Review date | Reviewer / role | Risks changed | Decision / evidence |
|---|---|---|---|
| [date] | [name / role] | [IDs] | [notes] |
