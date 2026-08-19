# Orgmetra structured interview plan

`orgmetra-interview-plan` creates candidate-neutral evidence for approving a structured interview **before** it is used with applicants.

The plan binds one requisition and authoritative Job to versioned job-analysis evidence, a predetermined question set, an exact question-to-competency mapping artifact, rating anchors, job-related competency references, and a bounded interviewer panel. The question set and mapping each carry their own immutable SHA-256 evidence digest, so a count of questions cannot be mistaken for proof that every governed competency is actually assessed. It keeps candidate identity, responses, scores, demographic attributes, model output, credentials, provider data, and free-form personal/value-bearing reason text out of the packet.

Every plan also carries a bounded positive `evidence_version` (1 through 2147483647) in canonical evidence. Version changes therefore change the SHA-256 audit correlation, and direct construction plus `dataclasses.replace(...)` revalidate the version fail closed. Version 1 is the default for the initial evidence schema; callers must increment it when the governed plan evidence is materially revised rather than treating a digest alone as semantic version identity.

Every trust-bearing reference uses its expected namespace plus a canonical, non-sentinel UUIDv4 suffix. That applies to the interview plan, requisition, Job, Job Analysis, question set, question-to-competency map, rating anchors, competencies, and panel actors. UUIDv1 and other UUID versions fail closed so timestamp/node-bearing identifiers cannot weaken the opaque-reference boundary. Human-readable/value-bearing suffixes such as names, job labels, protected-attribute labels, compensation values, or interviewer names are also rejected before canonical evidence is produced. The initial reason vocabulary is closed to the reviewed non-sensitive `approved_requisition_interview` value.

The object is not an interview result and cannot represent an approved employment decision. `human_confirmation_required` is fixed to `True`, `review_state` is fixed to `requires_human_approval`, and the next action tells an accountable reviewer to confirm job relatedness and the approved interview structure before activation. Direct construction and `dataclasses.replace(...)` re-run the same fail-closed invariants.

`repr(plan)` is fully redacted as `StructuredInterviewPlan(<redacted>)`, so routine logs and assertion failures do not expose governance correlations or evidence digests. Canonical JSON remains the explicit evidence serialization boundary.

For consistency and immutable audit correlation, evidence digests are lowercase SHA-256, competency and panel tuples must be sorted and unique, and timestamps are timezone-aware RFC 3339 values with fractional precision preserved. Opaque references are value-minimized correlation metadata, not anonymous data, and remain subject to purpose-bound authorization, least privilege, retention/export controls, and audit.

This package does not persist Job Analysis, requisitions, candidates, interview responses, or scores. Those remain separate Orgmetra boundaries and must use purpose-bound authorization, human review, and immutable audit/outbox evidence when they become authoritative writes.
