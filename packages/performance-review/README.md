# Orgmetra Performance Review

`orgmetra-performance-review` provides a small, transport-neutral evidence packet for preparing an accountable human performance review without copying person PII, rating values, free-form feedback, or model output into the governance envelope.

The packet correlates one opaque Person and Employment reference with a Job, performance cycle, governed criterion set, goal plan, exact criterion-observation snapshot, optional development plan, and reviewer. Every evidence artifact is represented by an opaque UUID-backed reference and, where integrity matters, an independent SHA-256 digest. **The packet does not assert that those independently supplied references already resolve to one authoritative employment/performance scope.** `scope_verification_state` is fixed to `requires_authoritative_resolution`; the authoritative HRIS/performance boundary must resolve that relationship before a rating is recorded.

The person reference is still sensitive correlating metadata. Hosts must enforce purpose-bound authorization, least privilege, retention/export controls, and immutable audit evidence around packet access. `reason_code` is not free-form metadata: the current reviewed vocabulary accepts only `scheduled_cycle_review`. New business reasons must be introduced through an explicit governed contract change rather than encoded into arbitrary lower-snake-case strings, preventing names, identifiers, or other unreviewed context from entering canonical evidence.

Every packet also carries a bounded positive integer `evidence_version` (default `1`). The version is part of canonical JSON and therefore changes the SHA-256 correlation digest when the reviewed evidence contract/version changes. Zero, negative, boolean, textual, and values above `2147483647` fail closed. The version identifies the review evidence envelope; it is not a rating, approval, or substitute for authoritative source-version verification.

## What this packet does not do

It does not calculate or persist a rating, write narrative feedback, infer performance, make an employment decision, modify compensation, execute a development action, or prove cross-record scope consistency by syntax alone. It does not replace the authoritative performance/criterion persistence boundary. Canonical JSON and SHA-256 provide correlation integrity only; they do not prove fairness, scientific validity, legal compliance, authoritative scope resolution, or that a human review actually occurred.

## Required review state

Every packet remains `requires_human_review`, with `decision_authority="human_review_only"`, `human_confirmation_required=True`, and `scope_verification_state="requires_authoritative_resolution"`. The fixed next action tells the reviewer to verify authoritative Employment/Job scope, review-period and performance-cycle alignment, governed criteria and goals, criterion-observation evidence, and any development-plan provenance before recording accountable human rating and feedback through the authoritative performance workflow.
