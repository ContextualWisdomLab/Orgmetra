# ADR-0006: Governed audit/outbox envelope

- **Status:** Accepted for the stacked implementation branch; not protected-main truth until merged.
- **Decision date:** 2026-08-17
- **Scope:** Orgmetra-owned audit/outbox event contract only. Durable database tables, dispatcher leases, retries, and retention remain separate persistence work.

## Context

Orgmetra mutations need portable event envelopes for asynchronous integration and durable, attributable evidence for later review. Copying mutable HR payloads into audit/event records would create a shadow system of record and enlarge the PII retention surface. Omitting actor, purpose, reason, evidence version, or accountable human confirmation would make high-impact employment changes difficult to explain and govern.

CloudEvents 1.0 provides a stable interoperable event envelope. NIST SP 800-92 requires organizations to protect log integrity and define accountable log-management processes. Orgmetra therefore needs one narrow contract that is portable enough for an outbox but strict enough for audit provenance.

## Decision

`orgmetra_hris_kernel.AuditOutboxEvent` is the canonical in-process envelope builder for HRIS mutations.

The contract:

1. Emits CloudEvents `specversion: 1.0`, stable event id, `urn:orgmetra:<service>` source, `orgmetra.*` event type, opaque subject reference, UTC event time, and JSON content type.
2. Carries tenant, actor, purpose, reason, evidence-version, and optional human-confirmation references as Orgmetra extension attributes.
3. Requires a confirmation reference for a high-impact event rather than manufacturing or inferring human review.
4. Carries only mutation result classification in `data`; mutable names, compensation, free-text evidence, and other HR payload fields stay in their authoritative bounded context.
5. Computes a deterministic SHA-256 digest over the canonical structured envelope so durable persistence can detect later mutation.
6. Does not claim persistence. The owning service must store the envelope and digest atomically with the business mutation before asynchronous delivery. Dispatcher state and delivery receipts belong to `integration_hub`; append-only review evidence belongs to `audit_provenance`.

## Consequences

- A buyer can trace an HRIS mutation to tenant, actor, purpose, reason, evidence version, and human confirmation without duplicating the underlying HR record.
- Event consumers receive a CloudEvents-compatible envelope while service extraction remains possible.
- The digest detects envelope mutation but is not, by itself, a durable tamper-proof audit store. Database immutability, access control, retention, export, and delivery-recovery controls remain mandatory.
- Downstream services must dereference authoritative records through published owner contracts rather than expecting copied PII in event payloads.

## Evidence

Focused regression evidence on the implementation branch covers CloudEvents shape, PII minimization, deterministic digest behavior, high-impact confirmation, timezone ambiguity, source/event namespace validation, and all public branches at 100% statement/branch coverage for the new module.

## References

See `docs/doctoring/REFERENCES.md` for CloudEvents v1.0.2 and NIST SP 800-92 in APA 7 format.