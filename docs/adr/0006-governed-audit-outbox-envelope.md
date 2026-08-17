# ADR-0006: Governed audit/outbox envelope and durable persistence

- **Status:** Accepted for the stacked implementation branch; not protected-main truth until merged.
- **Decision date:** 2026-08-17
- **Scope:** Orgmetra-owned audit envelope, immutable audit persistence, guarded outbox delivery state, tenant-safe atomic dispatcher claiming, expired-lease takeover, owner-bound completion/retry, database-budget-governed terminal dead-letter escalation, review hardening, and privileged recovery of an expired exhausted lease when its recorded final worker identity is permanently unavailable. Exponential retry policy, retention/export workflows, and external delivery receipts remain subsequent work.

## Context

Orgmetra mutations need portable event envelopes for asynchronous integration and durable, attributable evidence for later review. Copying mutable HR payloads into audit/event records would create a shadow system of record and enlarge the PII retention surface. Omitting actor, purpose, reason, evidence version, or accountable human confirmation would make high-impact employment changes difficult to explain and govern.

CloudEvents 1.0 provides a stable interoperable event envelope. NIST SP 800-92 requires protected, accountable log-management evidence. PostgreSQL row-level security and trigger semantics provide an Orgmetra-owned enforcement boundary for tenant isolation, append-only audit facts, and constrained delivery-state transitions. PostgreSQL documents `SKIP LOCKED` as suitable for avoiding lock contention among multiple consumers of queue-like tables; Orgmetra uses that primitive only for the inconsistent queue view where skipping work already locked by another dispatcher is the intended behavior.

A lease-based dispatcher also needs a crash boundary. Before the retry budget is exhausted, an expired lease can be atomically taken over as the next attempt. At the final allowed attempt, takeover must not manufacture attempt N+1. The normal path therefore keeps the row bound to the recorded stable worker reference after expiry, allowing that identity to append terminal escalation evidence. If that final identity is permanently lost, refusing all other recovery would strand the delivery forever; a separate operator-only path is therefore required, but only after both lease expiry and durable attempt-budget exhaustion and only with append-only operator-attributed escalation evidence.

Durable evidence also needs protection beyond ordinary row DML. Row-level update/delete triggers do not protect against PostgreSQL `TRUNCATE`, and untrusted object creation on a caller-controlled search path could alter which function or relation an otherwise-valid database boundary resolves. The review hardening migration therefore treats statement-level deletion and SQL name resolution as part of the same integrity boundary rather than as deployment assumptions. The operator recovery path also requires capability separation: granting its externally assignable role direct outbox UPDATE/INSERT rights would let the role emulate terminal transitions outside the narrower expired-lease function contract. The database therefore separates that external capability from a non-login, non-BYPASSRLS function owner with only the DML privileges the audited function requires.

## Decision

`orgmetra_hris_kernel.AuditOutboxEvent` is the canonical in-process envelope builder. Migrations 0003–0007 own durable persistence, claim/recovery, live-owner finalization, durable retry budget, dead-lettering, immutable escalation evidence, and attempt-exhaustion behavior. `database/migrations/0008_audit_outbox_review_hardening.sql` closes review-identified integrity and operability gaps without weakening those state-machine contracts.

The contract:

1. Emits CloudEvents `specversion: 1.0`, stable event id, `urn:orgmetra:<service>` source, `orgmetra.*` event type, opaque subject reference, UTC event time, and JSON content type.
2. Carries tenant, actor, purpose, reason, evidence-version, and optional human-confirmation references; high-impact events require confirmation.
3. Carries only result classification in `data`; names, compensation, free text, and other HR facts remain in their authoritative bounded context.
4. Exposes deterministic `canonical_json()` bytes and SHA-256 `content_digest()`; PostgreSQL reparses the envelope, enforces the exact allowlisted shape, verifies tenant/event binding, and recomputes the digest.
5. Stores immutable event evidence in `audit_event_record` and mutable delivery coordination in `outbox_delivery_record`; terminal failure metadata is normalized into append-only `outbox_delivery_escalation_record`.
6. Permits guarded `pending -> leased -> delivered`, pre-exhaustion `leased -> pending`, pre-exhaustion expired `leased -> leased` takeover, and exhausted `leased -> dead_lettered` only with matching immutable escalation evidence. Delivery identity, audit binding, and stored retry budget never change.
7. `record_audit_outbox_event(...)` atomically inserts audit evidence and its pending delivery in the owning business transaction.
8. `claim_outbox_delivery(...)` requires exact tenant context, canonical target/worker identifiers, a bounded lease, deterministic due-work order, `FOR UPDATE ... SKIP LOCKED`, and increments the attempt count exactly once per ownership grant. Live leases and exhausted rows are excluded.
9. `complete_outbox_delivery(...)` and `retry_outbox_delivery(...)` require the exact owner of a still-live lease. Retry preserves the attempt count and fails closed when the stored budget is exhausted.
10. `dead_letter_outbox_delivery(...)` is the normal worker terminal path. It requires exact tenant context, the recorded worker identity, durable budget exhaustion, bounded failure classification, and immutable escalation evidence. The recorded worker may terminalize its expired final lease without creating attempt N+1.
11. `operator_dead_letter_expired_outbox_delivery(...)` is a distinct privileged recovery path for a permanently unavailable final worker. It accepts only an already-expired `leased` row whose stored attempt count is exhausted, validates operational UUIDs plus opaque operator identity and lower `snake_case` failure code, row-locks the delivery, inserts operator-attributed immutable escalation evidence, and then transitions through the same guarded `dead_lettered` invariant. `PUBLIC` has no execute privilege. Migration 0008 owns two NOLOGIN/NOBYPASSRLS roles: `orgmetra_outbox_recovery_owner` owns this sole `SECURITY DEFINER` recovery function and holds only its required transport-table privileges, while externally assignable `orgmetra_outbox_operator` receives EXECUTE only and no direct outbox UPDATE or escalation INSERT privilege. Login identities receive operator membership only through explicit purpose-bound provisioning.
12. Update/delete and statement-level `TRUNCATE` cannot erase immutable audit evidence. Outbox delivery state also rejects `TRUNCATE` so transport history cannot be bulk-deleted around the state machine.
13. Audit/outbox boundary functions pin `search_path = pg_catalog, public, pg_temp`; migration 0008 revokes `CREATE` on schema `public` from `PUBLIC`. Normal persistence/dispatcher functions remain security-invoker boundaries. The operator recovery function is the only `SECURITY DEFINER` exception and is owned by the hardened non-login recovery role, whose schema `CREATE` privilege is revoked immediately after ownership handoff.
14. The immutable envelope validator uses deterministic C-collated key ordering/comparison and validates the UTC timestamp lexically plus calendar/time fields instead of performing session-sensitive `timestamptz` input parsing inside an `IMMUTABLE` function.
15. A partial `outbox_delivery_due_work_index` serves pending/leased queue scans without indexing terminal rows. Migration 0008 builds it with `CREATE INDEX CONCURRENTLY`; the migration runner must therefore execute this migration outside an explicit transaction block so established queues do not block writers during index construction.

## Consequences

- Buyers can trace HRIS mutations to tenant, actor, purpose, reason, evidence version, and human confirmation without copying authoritative HR payloads.
- Immutable audit facts and mutable delivery coordination remain distinct relations; retries and leases cannot rewrite historical evidence.
- Multiple dispatcher workers have a bounded tenant-scoped claim primitive, while neither ordinary takeover nor retry can exceed `maximum_attempt_count`.
- Normal worker finalization remains capability-bound. A separate operator recovery mechanism prevents an exhausted final lease from becoming permanently stranded without allowing takeover of live or retryable work, and the externally assignable operator role cannot bypass the function through direct transport-table DML.
- Audit and delivery history resist both row mutation and bulk `TRUNCATE`, and database boundary resolution no longer depends on a caller-controlled schema path.
- The due-work index can be introduced without blocking queue writers, at the cost of requiring a migration runner that supports PostgreSQL's non-transactional concurrent-index semantics and explicit handling of any invalid-index residue after an interrupted build.
- Permanent downstream failures can leave normal dispatch only with durable budget exhaustion plus immutable escalation evidence. Dead-lettering still does not prove downstream acknowledgement; exponential/backoff policy selection and external delivery receipts remain required for production-ready asynchronous delivery.
- Downstream services dereference authoritative records through published owner contracts rather than expecting copied PII in events.

## Evidence

The branch contains test-first application and PostgreSQL regressions for deterministic CloudEvents bytes/digest, PII minimization, human confirmation, timezone normalization, tenant isolation, atomic audit/outbox insertion, immutable audit evidence, dispatcher lease ownership, crash recovery, bounded retry, attempt-N+1 denial, owner-bound terminalization, immutable escalation evidence, and reserved UUID sentinels.

Review hardening added a focused PostgreSQL RED contract before migration 0008. That contract requires statement-level audit/outbox TRUNCATE denial, trusted search paths on every audited dispatcher/recovery boundary, deterministic/session-independent immutable envelope validation, the due-work partial index, and operator terminalization of only an expired exhausted lease with immutable operator-attributed escalation evidence. The operator regression now executes recovery through the externally assignable NOLOGIN capability role, proves both service-owned recovery roles are non-superuser and NOBYPASSRLS, and proves the operator role cannot mutate outbox state or insert escalation evidence directly. Additional review regressions make every captured dispatcher/dead-letter `psql` assertion fail on SQL errors, execute audit persistence sessions with explicit tenant context, assert the exact duplicate-delivery primary-key failure for transaction rollback, prove non-UTC application timestamps normalize to UTC, discover all executable migration/PostgreSQL-contract artifacts for provenance, and validate the database contract across all migrations rather than a hardcoded prefix.

Exact-current-head hosted evidence is required after every branch mutation. Queued, cancelled, stale, predecessor, or model-only results are non-passing and do not change this ADR’s protected-main status.

## References

See `docs/doctoring/REFERENCES.md` for CloudEvents v1.0.2, NIST SP 800-92, and PostgreSQL 16 row-security, role, privilege, SECURITY DEFINER, index-concurrency, locking, trigger, and date/time documentation in APA 7 style.
