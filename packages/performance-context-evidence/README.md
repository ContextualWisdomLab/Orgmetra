# Orgmetra Performance Context Evidence

## Status

This package is **active-PR truth on PR #93**. It is not protected-`develop` truth until that PR is independently reviewed and merged through enforceable repository gates.

## Why this exists

A performance score can reflect more than the worker. Opportunity to perform, work conditions, organizational membership, and manager-related context can alter what is observable. Orgmetra therefore keeps reviewed context provenance beside criterion evidence instead of silently treating every outcome as context-free.

`PerformanceContextEvidencePacket` is deliberately **not** a rating-adjustment engine. It carries only bounded references, a half-open business-time window, and SHA-256 provenance for reviewed context snapshots. Raw HR values, performance ratings, and manager identity stay outside the packet.

## Governed evidence

The packet binds:

- tenant, Employment, Job, and performance-cycle references;
- one or more sorted, unique Assignment and Organization references so later analysis can re-resolve multiple-membership structure;
- `context_effective_from` / `context_effective_to` as a nonempty half-open business-time interval;
- SHA-256 provenance for opportunity-to-perform, broader work context, manager context, and reviewed membership weights;
- distinct requester and human reviewer references;
- purpose, reason, evidence version, and system-recorded time.

The packet is permanently constrained to `context_covariate_evidence_only`, `requires_human_review`, `not_authorized_for_performance_rating`, and `not_authorized_for_employment_decision`.

## Next action

Before using the packet in a validity or workforce analysis, re-resolve the referenced Employment, Job, performance cycle, Assignments, and Organizations through authoritative Orgmetra boundaries at the reviewed business-time window. Verify the four provenance digests against the reviewed source snapshots. Use the result only as context-covariate provenance; do not automatically change an individual rating, compensation action, hiring decision, promotion, termination, or other employment decision.

## Safety and integrity

- Exact built-in runtime primitives are required before UUID parsing, equality, ordering, hashing, or serialization.
- Assignment and Organization collections are bounded, deterministic tuples.
- Canonical evidence excludes raw context values and manager identity.
- A process-local issuance registry detects post-construction mutation and conflicting reuse of a live tenant-qualified packet reference. Exact idempotent duplicates share one live binding, so garbage-collecting one duplicate cannot reopen the reference while another duplicate remains live. Durable cross-process uniqueness still belongs to authoritative persistence/audit boundaries; this in-process registry is defense-in-depth, not a database substitute.
- The installed wheel is hash-bound and tested at exact 100% owned production statement and branch coverage by `Performance Context Evidence Quality`.
