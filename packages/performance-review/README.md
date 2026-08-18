# Orgmetra Performance Review

`orgmetra-performance-review` provides a small, transport-neutral evidence packet for preparing an accountable human performance review without copying person PII, rating values, free-form feedback, or model output into the governance envelope.

The packet binds one opaque person and Employment reference to the authoritative Job, performance cycle, governed criterion set, goal plan, exact criterion-observation snapshot, optional development plan, and reviewer. Every evidence artifact is represented by an opaque UUID-backed reference and, where integrity matters, an independent SHA-256 digest.

The person reference is still sensitive correlating metadata. Hosts must enforce purpose-bound authorization, least privilege, retention/export controls, and immutable audit evidence around packet access.

## What this packet does not do

It does not calculate or persist a rating, write narrative feedback, infer performance, make an employment decision, modify compensation, or execute a development action. It does not replace the authoritative performance/criterion persistence boundary. Canonical JSON and SHA-256 provide correlation integrity only; they do not prove fairness, scientific validity, legal compliance, or that a human review actually occurred.

## Required review state

Every packet remains `requires_human_review`, with `decision_authority="human_review_only"` and `human_confirmation_required=True`. The fixed next action tells the reviewer to verify Employment/Job scope, review-period and performance-cycle alignment, governed criteria and goals, criterion-observation evidence, and any development-plan provenance before recording accountable human rating and feedback through the authoritative performance workflow.
