# ADR 0104: Governed Job qualification-rule review

- Status: proposed on active PR; not protected-main truth until merged.
- Date: 2026-08-24

## Context

Protected `develop` models Job Analysis versions, Tasks, FJA and KSAO evidence, and the PRD requires qualification rules, but there is no bounded governance object proving which job-analysis evidence supported a proposed qualification rule before that rule can influence recruiting or selection.

OPM describes job analysis as the systematic linkage of job tasks and competencies/KSAs and states that job-analysis information supports recruitment, qualification, assessment and selection. OPM also emphasizes evidence for task/KSA importance and current job requirements. The Uniform Guidelines on Employee Selection Procedures provide a federal framework for the proper use and documentation of selection procedures. Orgmetra uses these public sources as design evidence only; this package does not decide legal compliance, reproduce licensed standards, or validate a selection procedure.

## Decision

Create an Orgmetra-owned `JobQualificationRuleReviewPacket` as PII-minimized, human-reviewed proposal evidence.

The packet binds tenant and authoritative Job scope, one Job Analysis snapshot reference/digest, one opaque qualification-rule artifact reference/digest, Task/KSAO/source linkage digests, a controlled rule category, a business-effective date, distinct requester/reviewer correlations, a controlled review reason, bounded evidence version, human review time, and an Orgmetra-generated system-recorded UTC issuance time.

The controlled category describes only the type of job requirement evidence (`credential_requirement`, `education_training_requirement`, `experience_requirement`, `knowledge_skill_ability_requirement`, or `task_or_work_requirement`). It does not record candidate qualification, cut scores, assessment outcomes, legal status, or an autonomous eligibility decision.

Every packet is fixed to human review and `not_authorized_for_candidate_or_employment_decision`. Before a reviewed rule changes authoritative Job/Job Analysis truth or is used in recruiting/selection, the host must re-resolve exact tenant/Job/snapshot/artifact/linkage evidence and reviewer authority at the relevant business-time coordinate and atomically preserve immutable audit/outbox evidence.

## Privacy and integrity consequences

Canonical evidence excludes Person/candidate identifiers and PII, compensation, assessment scores, raw rule or qualification text, credentials, prompts/model output, and free-form review text. Operational HRIS references use the core non-sentinel UUID contract; packet-owned artifact and actor correlations require opaque UUIDv4 references.

Trust-bearing primitives are exact built-in types. Malformed/noncanonical IDs or SHA-256, unreviewed categories/reasons, actor overlap, invalid evidence versions, caller-supplied system time, future review time, mutable fixed governance, and post-issuance mutation fail closed. The process-local issuance registry is defense in depth only; durable identity, uniqueness, authorization, and audit remain host responsibilities.

## Alternatives rejected

- **Store free-form minimum-qualification text in the governance packet.** Rejected because it expands durable sensitive/business text without improving provenance; the reviewed artifact is referenced and hashed instead.
- **Evaluate candidates inside this packet.** Rejected because job-rule governance and candidate evidence/selection decisions are distinct high-impact boundaries.
- **Infer rules directly from an LLM.** Rejected because model output is untrusted draft evidence and cannot substitute for Job Analysis linkage or accountable human review.
- **Treat a qualification category as proof of validity or legality.** Rejected because jurisdiction, job relatedness, validity and applicant application require separate authoritative review.
