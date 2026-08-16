# ADR-0006: Governed audit/outbox envelope and durable persistence

- **Status:** Accepted for the stacked implementation branch; not protected-main truth until merged.
- **Decision date:** 2026-08-17
- **Scope:** Orgmetra-owned audit envelope, immutable audit persistence, and guarded outbox delivery state. Dispatcher claiming, retry scheduling policy, retention/export workflows, and external delivery receipts remain subsequent work.

## Context

Orgmetra mutations need portable event envelopes for asynchronous integration and durable, attributable evidence for later review. Copying mutable HR payloads into audit/event records would create a shadow system of record and enlarge the PII retention surface. Omitting actor, purpose, reason, evidence version, or accountable human confirmation would make high-impact employment changes difficult to explain and govern.

CloudEvents 1.0 provides a stable interoperable event envelope. NIST SP 800-92 requires protected, accountable log-management evidence. PostgreSQL row-level security and trigger semantics provide an Orgmetra-owned enforcement boundary for tenant isolation, append-only audit facts, and constrained delivery-state transitions.

## Decision

`orgmetra_hris_kernel.AuditOutboxEvent` is the canonical in-process envelope builder for HRIS mutations. `database/migrations/0003_audit_outbox_persistence.sql` is the durable persistence boundary for that envelope.

The contract:

1. Emits CloudEvents `specversion: 1.0`, stable event id, `urn:orgmetra:<service>` source, `orgmetra.*` event type, opaque subject reference, UTC event time, and JSON content type.
2. Carries tenant, actor, purpose, reason, evidence-version, and optional human-confirmation references as Orgmetra extension attributes.
3. Requires a confirmation reference for a high-impact event rather than manufacturing or inferring human review.
4. Carries only mutation result classification in `data`; mutable names, compensation, free-text evidence, and other HR payload fields stay in their authoritative bounded context.
5. Exposes `canonical_json()` as the exact deterministic UTF-8 JSON representation to persist and digest; `content_digest()` is SHA-256 over those exact bytes.
6. Stores immutable event evidence in `audit_event_record`. PostgreSQL reparses the envelope, requires the exact allowlisted field shape, verifies event/tenant binding and high-impact confirmation, and recomputes SHA-256 over the supplied canonical bytes before accepting the row.
7. Stores asynchronous delivery lifecycle separately in `outbox_delivery_record`, preserving 3NF and preventing dispatcher state from rewriting immutable audit evidence.
8. Permits only guarded `pending -> leased -> delivered` delivery transitions, plus `leased -> pending` retry recovery. Delivery identity and audit binding never change; delivered records are terminal.
9. `record_audit_outbox_event(...)` inserts the immutable audit fact and pending delivery record in one PostgreSQL statement. The owning service calls it inside the same database transaction as its business mutation so any later statement failure rolls the whole transaction back.
10. Forces tenant row-level security on both new tables through the existing `current_tenant_record_id()` contract.

## Consequences

- A buyer can trace an HRIS mutation to tenant, actor, purpose, reason, evidence version, and human confirmation without duplicating the underlying HR record.
- Event consumers receive a CloudEvents-compatible envelope while service extraction remains possible.
- A digest mismatch, extra top-level payload field, tenant/event-id mismatch, or missing high-impact confirmation fails closed at the durable database boundary rather than relying only on application validation.
- Immutable audit facts and mutable delivery coordination remain distinct relations; retries and leases cannot rewrite historical evidence.
- The current slice deliberately does not claim a production dispatcher. A later dispatcher must claim work with concurrency-safe row locking, define bounded retry/backoff and lease-expiry recovery, publish delivery receipts, and prove crash/restart behavior before audit delivery is called production-ready.
- Retention, customer export, backup/restore validation, and privileged audit access remain explicit operational controls rather than properties inferred from the digest alone.
- Downstream services dereference authoritative records through published owner contracts rather than expecting copied PII in event payloads.

## Evidence

The stacked branch contains test-first regression coverage for CloudEvents shape, PII minimization, deterministic canonical bytes/digest behavior, high-impact confirmation, timezone ambiguity, source/event namespace validation, runtime type confusion, and identifier validity. The PostgreSQL contract additionally exercises atomic audit/outbox insertion, database digest verification, PII-bearing extra-field rejection, missing-confirmation rejection, append-only audit protection, guarded lease/delivery transitions, terminal-state immutability, and rollback on outbox failure.

Focused Python evidence is branch-local. PostgreSQL execution and the complete Foundation CI/central workflow set remain non-passing until this stacked PR can be reconciled onto the protected branch after its dependency integrates; no queued, absent, predecessor, or model-only result is treated as GREEN.

## References

See `docs/doctoring/REFERENCES.md` for CloudEvents v1.0.2, NIST SP 800-92, and PostgreSQL 16 trigger/locking documentation in APA 7 style.
