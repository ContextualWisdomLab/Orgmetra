# Orgmetra structured interview plan

`orgmetra-interview-plan` creates candidate-neutral evidence for approving a structured interview **before** it is used with applicants.

The plan binds one requisition and authoritative Job to versioned job-analysis evidence, a predetermined question set, an exact question-to-competency mapping artifact, rating anchors, job-related competency references, and a bounded interviewer panel. The question set and mapping each carry their own immutable SHA-256 evidence digest, so a count of questions cannot be mistaken for proof that every governed competency is actually assessed. It keeps candidate identity, responses, scores, demographic attributes, model output, credentials, and provider data out of the packet.

The object is not an interview result and cannot represent an approved employment decision. `human_confirmation_required` is fixed to `True`, `review_state` is fixed to `requires_human_approval`, and the next action tells an accountable reviewer to confirm job relatedness and the approved interview structure before activation.

For consistency and immutable audit correlation, all governance references are bounded opaque namespaced identifiers, evidence digests are lowercase SHA-256, competency and panel tuples must be sorted and unique, and timestamps are timezone-aware RFC 3339 values with fractional precision preserved.

This package does not persist Job Analysis, requisitions, candidates, interview responses, or scores. Those remain separate Orgmetra boundaries and must use purpose-bound authorization, human review, and immutable audit/outbox evidence when they become authoritative writes.
