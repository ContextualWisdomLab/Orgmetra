# ADR-0006: Governed audit/outbox envelope

- **Status:** Accepted across stacked implementation branches; not protected-main truth until merged dependency-first.
- **Decision date:** 2026-08-17
- **Scope:** Orgmetra-owned audit/outbox event contract plus immutable transactional persistence. Dispatcher leases, retries, delivery receipts, retention execution, and export workflows remain later operational work.

## Context

Orgmetra mutations need portable event envelopes for asynchronous integration and durable, attributable evidence for later review. Copying mutable HR payloads into audit/event records would create a shadow system of record and enlarge the PII retention surface. Omitting actor, purpose, reason, evidence version, or accountable human confirmation would make high-impact employment changes difficult to explain and govern.

CloudEvents 1.0 provides a stable interoperable event envelope. NIST SP 800-92 requires organizations to protect log integrity and define accountable log-management processes. Orgmetra therefore needs one narrow contract that is portable enough for an outbox but strict enough for audit provenance, plus a transaction boundary that cannot commit an HR mutation after its required audit append fails.

## Decision

`orgmetra_hris_kernel.AuditOutboxEvent` is the canonical in-process envelope builder for HRIS mutations. `audit_outbox_record` is the Orgmetra-owned immutable persistence boundary for the exact canonical envelope bytes.

The contract:

1. Emits CloudEvents `specversion: 1.0`, stable event id, `urn:orgmetra:<service>` source, `orgmetra.*` event type, opaque subject reference, UTC event time, and JSON content type.
2. Carries tenant, actor, purpose, reason, evidence-version, and optional human-confirmation references as Orgmetra extension attributes.
3. Requires a confirmation reference for a high-impact event rather than manufacturing or inferring human review.
4. Carries only mutation result classification in `data`; mutable names, compensation, free-text evidence, and other HR payload fields stay in their authoritative bounded context.
5. Exposes `canonical_json()` as the exact compact UTF-8 text that is persisted and hashed. `content_digest()` computes SHA-256 over those exact bytes.
6. Stores `event_envelope_text` and `event_content_digest` in `audit_outbox_record` inside the same caller-controlled database transaction as the owning Orgmetra business mutation.
7. Recomputes SHA-256 in PostgreSQL from the stored envelope bytes before accepting the append; rejects envelope/event-id or envelope/tenant mismatches; and fails closed when a high-impact envelope lacks accountable human confirmation.
8. Forces tenant row-level security and rejects UPDATE/DELETE on committed audit-outbox records. Delivery state must therefore live separately from immutable audit evidence.
9. Does not claim asynchronous delivery. Dispatcher leasing, retry/backoff, dead-letter handling, delivery receipts, retention execution, and export workflows remain separate operational slices.

## Consequences

- A buyer can trace an HRIS mutation to tenant, actor, purpose, reason, evidence version, and human confirmation without duplicating the underlying HR record.
- Event consumers receive a CloudEvents-compatible envelope while service extraction remains possible.
- A failed or forged audit append can abort the same transaction as the business mutation, eliminating a known path to unaudited committed HR changes when callers use the required transaction boundary.
- Database immutability protects committed envelope evidence while mutable delivery concerns remain outside the evidence row.
- The SHA-256 digest detects byte-level envelope mutation but is not, by itself, proof against privileged database replacement or infrastructure compromise. Backup integrity, access control, retention/export policy, monitoring, and recovery evidence remain mandatory.
- Downstream services must dereference authoritative records through published owner contracts rather than expecting copied PII in event payloads.

## Evidence

The envelope branch covers CloudEvents shape, PII minimization, deterministic digest behavior, high-impact confirmation, timezone ambiguity, source/event namespace validation, and all public branches of the new module. The transactional persistence branch adds regression coverage for exact producer-byte serialization, database digest recomputation, successful business-write + audit append commit, rollback of the business write after a forged audit digest, append-only mutation rejection, tenant/envelope mismatch rejection, high-impact confirmation enforcement, and forced-RLS metadata.

Hosted PostgreSQL and full repository evidence remain non-transferable until the exact stacked head runs the corresponding CI job successfully.

## References

See `docs/doctoring/REFERENCES.md` for CloudEvents v1.0.2 and final NIST SP 800-92 in APA 7 format.
