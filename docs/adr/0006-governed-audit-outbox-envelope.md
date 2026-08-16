# ADR-0006: Governed audit/outbox envelope and durable persistence

- **Status:** Accepted for the stacked implementation branch; not protected-main truth until merged.
- **Decision date:** 2026-08-17
- **Scope:** Orgmetra-owned audit envelope, immutable audit persistence, guarded outbox delivery state, tenant-safe atomic dispatcher claiming, and expired-lease takeover. Retry/backoff scheduling, owner-aware completion/retry functions, retention/export workflows, dead-letter/escalation policy, and external delivery receipts remain subsequent work.

## Context

Orgmetra mutations need portable event envelopes for asynchronous integration and durable, attributable evidence for later review. Copying mutable HR payloads into audit/event records would create a shadow system of record and enlarge the PII retention surface. Omitting actor, purpose, reason, evidence version, or accountable human confirmation would make high-impact employment changes difficult to explain and govern.

CloudEvents 1.0 provides a stable interoperable event envelope. NIST SP 800-92 requires protected, accountable log-management evidence. PostgreSQL row-level security and trigger semantics provide an Orgmetra-owned enforcement boundary for tenant isolation, append-only audit facts, and constrained delivery-state transitions. PostgreSQL documents `SKIP LOCKED` as suitable for avoiding lock contention among multiple consumers of queue-like tables; Orgmetra uses that primitive only for the inconsistent queue view where skipping work already locked by another dispatcher is the intended behavior.

A lease-based dispatcher also needs a crash boundary. Treating `leased` as permanently ineligible would strand a delivery forever when the owning worker dies after claiming it. Recovery therefore has to distinguish a live lease from an expired ownership grant, without deleting or rewriting the immutable audit fact.

## Decision

`orgmetra_hris_kernel.AuditOutboxEvent` is the canonical in-process envelope builder for HRIS mutations. `database/migrations/0003_audit_outbox_persistence.sql` is the durable persistence boundary for that envelope, and `database/migrations/0004_outbox_delivery_claim.sql` adds the dispatcher claim and expired-lease recovery boundary without changing immutable audit bytes.

The contract:

1. Emits CloudEvents `specversion: 1.0`, stable event id, `urn:orgmetra:<service>` source, `orgmetra.*` event type, opaque subject reference, UTC event time, and JSON content type.
2. Carries tenant, actor, purpose, reason, evidence-version, and optional human-confirmation references as Orgmetra extension attributes.
3. Requires a confirmation reference for a high-impact event rather than manufacturing or inferring human review.
4. Carries only mutation result classification in `data`; mutable names, compensation, free-text evidence, and other HR payload fields stay in their authoritative bounded context.
5. Exposes `canonical_json()` as the exact deterministic UTF-8 JSON representation to persist and digest; `content_digest()` is SHA-256 over those exact bytes.
6. Stores immutable event evidence in `audit_event_record`. PostgreSQL reparses the envelope, requires the exact allowlisted field shape, verifies event/tenant binding and high-impact confirmation, and recomputes SHA-256 over the supplied canonical bytes before accepting the row.
7. Stores asynchronous delivery lifecycle separately in `outbox_delivery_record`, preserving 3NF and preventing dispatcher state from rewriting immutable audit evidence.
8. Permits guarded `pending -> leased -> delivered` delivery transitions, `leased -> pending` retry recovery, and only after lease expiry an atomic `leased -> leased` ownership takeover. Delivery identity and audit binding never change; delivered records are terminal. Every new ownership grant must expire strictly after the transaction timestamp.
9. `record_audit_outbox_event(...)` inserts the immutable audit fact and pending delivery record in one PostgreSQL statement. The owning service calls it inside the same database transaction as its business mutation so any later statement failure rolls the whole transaction back.
10. Forces tenant row-level security on both new tables through the existing `current_tenant_record_id()` contract.
11. `claim_outbox_delivery(...)` requires its requested tenant to equal the active tenant context, validates delivery-target and opaque worker identifiers, bounds a lease to 1–3600 seconds, and claims at most one due pending or expired leased delivery in deterministic order.
12. The claim reads candidates with `FOR UPDATE ... SKIP LOCKED`, updates the chosen row through the transition guard, increments the attempt count once, sets a future lease, and returns the immutable canonical event plus digest needed by the dispatcher. A live lease is skipped rather than stolen or duplicated.
13. When the selected row carries an expired lease, takeover increments the attempt count again and writes `last_failure_code = 'lease_expired'`. This makes worker loss observable while preserving the original event, target, recorded time, delivery identity, and audit binding. A partial index over leased expiry coordinates bounds recovery lookup cost.

## Consequences

- A buyer can trace an HRIS mutation to tenant, actor, purpose, reason, evidence version, and human confirmation without duplicating the underlying HR record.
- Event consumers receive a CloudEvents-compatible envelope while service extraction remains possible.
- A digest mismatch, extra top-level payload field, tenant/event-id mismatch, or missing high-impact confirmation fails closed at the durable database boundary rather than relying only on application validation.
- Immutable audit facts and mutable delivery coordination remain distinct relations; retries and leases cannot rewrite historical evidence.
- Multiple dispatcher workers have a bounded, tenant-scoped claim primitive that skips rows already locked by another consumer, refuses live-lease theft, and can recover work after an ownership lease actually expires.
- Crash recovery no longer requires rewriting a leased row back to pending first. The same locked claim operation can take over an expired lease, preserving one-row ownership while recording the failed attempt.
- The current slice still does not claim production-ready delivery completion or retry policy. A later bounded slice must define owner-aware completion/release functions, bounded retry/backoff, dead-letter/escalation behavior, external delivery receipts, and crash/restart evidence before audit delivery is called production-ready.
- Retention, customer export, backup/restore validation, and privileged audit access remain explicit operational controls rather than properties inferred from the digest alone.
- Downstream services dereference authoritative records through published owner contracts rather than expecting copied PII in event payloads.

## Evidence

The stacked branch contains test-first regression coverage for CloudEvents shape, PII minimization, deterministic canonical bytes/digest behavior, high-impact confirmation, timezone ambiguity, source/event namespace validation, runtime type confusion, and identifier validity. The PostgreSQL contract additionally exercises atomic audit/outbox insertion, database digest verification, PII-bearing extra-field rejection, missing-confirmation rejection, append-only audit protection, guarded lease/delivery transitions, terminal-state immutability, rollback on outbox failure, rejection of already-expired new leases, deterministic due-work claiming, live-lease exclusion, tenant-context binding, opaque worker identity, bounded lease duration, and takeover of a lease that expires after a successful claim with a second attempt plus `lease_expired` evidence.

Focused Python evidence is branch-local. The PostgreSQL claim/recovery contract is wired into Foundation CI, but the current local execution environment has no PostgreSQL client/server; database execution and the complete Foundation CI/central workflow set therefore remain non-passing until exact-head hosted evidence completes. No queued, absent, predecessor, or model-only result is treated as GREEN.

## References

See `docs/doctoring/REFERENCES.md` for CloudEvents v1.0.2, NIST SP 800-92, and PostgreSQL locking/current-time documentation in APA 7 style.
