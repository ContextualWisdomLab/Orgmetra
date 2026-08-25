# Orgmetra Position Lifecycle Review

This package records **human-reviewed evidence for a proposed lifecycle change to an existing Position**. It is deliberately not the authoritative Position mutation boundary.

## Why it exists

Current Orgmetra `develop` product truth already treats `Job`, `Position`, and `Assignment` as separate HRIS facts and recognizes Position statuses `open`, `active`, `frozen`, `closed`, and `abolished`. Repository control is separate from that product claim: an **effective organization ruleset** governs the default branch with pull-request integration, two approvals, stale-review dismissal, last-push approval, required conversation resolution, central required workflows, and non-fast-forward/deletion protection. Repository-governance issue #89 remains open for the narrower acquisition-grade gaps around routine administrator `always` bypass and executable proof that every applicable Orgmetra-local gate is fail-closed required. A commercial HRIS also needs review evidence before a seat is frozen, closed, abolished, or reactivated, because those changes can alter staffing availability and downstream workforce reporting.

`PositionLifecycleChangeReviewPacket` binds:

- tenant and Position operational UUIDs;
- one packet-owned UUIDv4 change correlation;
- current/proposed lifecycle status and business-effective date;
- exact reviewed Position and Assignment snapshot SHA-256 digests;
- pseudonymous requester/reviewer UUIDv4 actor correlations with separation;
- controlled reason and human review outcome;
- evidence schema version 1;
- human-review time and later-or-equal system-recorded UTC time.

It intentionally carries **no Person/candidate identity, name, email, compensation, assessment, rating, allocation value, credential, prompt, or model output**.

## Authority boundary

Even an `approved_for_authoritative_resolution` review remains:

- `human_reviewed`;
- `requires_authoritative_resolution`;
- `not_authorized_to_apply`;
- `human_review_only`.

Before a lifecycle mutation, the Orgmetra host must freshly re-resolve tenant-qualified bitemporal Position and Assignment truth at the requested business/system coordinate, re-resolve requester/reviewer authority, prove staffing safety, validate the reviewed evidence, and commit the actual Position mutation with immutable audit/outbox in the authoritative transaction. A rejected review must not be applied.

The packet permits reviewed transitions among normal seat states but treats `abolished` as terminal. No-op status changes are rejected. A reason token is tied to the proposed state so a valid token cannot be reused with different lifecycle semantics.

## Integrity boundary

Trust-bearing scalar values require exact built-in runtime types. Canonical evidence is deterministic JSON with SHA-256 content digest and a redacted routine representation. A process-local issuance seal detects post-construction field rewriting, while a live tenant-qualified change-reference binding prevents one correlation from denoting conflicting evidence while any duplicate packet remains alive. These are defense-in-depth controls only; durable uniqueness and mutation authorization belong to authoritative persistence/audit.

## Scope

This package writes only Orgmetra evidence. It does not modify Keyverse, Naruon, Contextual Orchestrator, or another dedicated-writer repository and does not query a foreign application table.
