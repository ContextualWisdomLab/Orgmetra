# ADR 0309: Idempotent document-record persistence under uncertain outcomes

## Status

Proposed. This ADR describes the stacked implementation for issue #309 and is not protected-`develop` truth until its prerequisites and this change integrate normally.

## Problem

ADR 0107 and migrations 0021–0023 make one `document_record` immutable, tenant-scoped, evidence-bound, unique-key JSON safe, and byte-canonical. Those invariants prevent duplicate durable identities from being silently accepted, but a uniqueness error is not an idempotent result contract.

A caller can lose the response after PostgreSQL commits. If it retries the same logical persistence command, the owner must distinguish that retry from a different command that reused the same key. Treating a generic unique violation as success would conflate those cases; generating new audit/outbox references on every retry would also make one logical command appear as multiple durable events.

The lock boundary must remain short. Document parsing, OCR, model inference, artifact transfer, or any other network/compute work is not permitted inside the database transaction used for retry arbitration.

## Decision

`document_records` owns a tenant-scoped `document_record_persist_receipt` and the `persist_document_record_once(...)` transaction boundary.

The command accepts one opaque, purpose-bound idempotency key of the form `document-record-persist-<uuid-v4>`. It computes a server-side SHA-256 semantic digest over the complete governed persistence command, excluding only PostgreSQL-owned result time. The key itself is not part of the semantic digest; it identifies a retry family rather than changing document semantics.

Before reading replay state or inserting a document, the function acquires `pg_advisory_xact_lock(hashtextextended(...))` over tenant + `document_records` namespace + key. The lock exists only until the current transaction ends. A same-key concurrent caller therefore waits until the first transaction commits or rolls back. No external I/O occurs while this lock is held.

After the lock:

- no receipt means the function inserts exactly one `document_record`, derives a receipt digest from the committed identity/result, and inserts one append-only receipt in the same transaction;
- an existing receipt with the same semantic digest returns the original document identity, document/audit/outbox references, semantic digest, receipt digest, and original database-owned `recorded_at`;
- an existing receipt with a different semantic digest fails closed before any second document write.

The receipt carries no document bytes, credentials, names, free-form HR content, compensation, ratings, or other duplicated Person/Employment truth. It stores only tenant identity, the opaque idempotency key, semantic digest, committed document identity, receipt digest, and system time. It is FORCE-RLS protected and append-only, including TRUNCATE protection.

The implementation adds a tenant-qualified unique key to `document_record` so the receipt can use a composite `(tenant_record_id, document_record_id)` foreign key. This preserves the bounded-context invariant that a receipt cannot point at a document from another tenant even if an otherwise valid UUID is supplied.

## Alternatives considered

**Return success on a unique violation.** Rejected. A uniqueness violation does not prove that the existing row came from the same semantic command.

**Retry heuristics in `talent_acquisition` or another consumer.** Rejected. Persistence replay truth belongs to `document_records`; copying mutable owner logic would create two authorities.

**Hold an explicit transaction open around upstream document processing.** Rejected. That would create the long-lived idle/lock behavior this architecture forbids. All expensive work must finish before entering `persist_document_record_once(...)`.

**Rely only on `INSERT ... ON CONFLICT`.** Rejected for this increment because the owner must compare a complete semantic digest and return the original result as one contract, not merely suppress a duplicate insert. The transaction-scoped advisory lock follows the already-protected People mutation pattern and makes the replay branch explicit.

## Evidence and acceptance

`tests/test_document_record_idempotency_postgres.sh` exercises real PostgreSQL sessions. It proves same-key/same-semantic retry convergence, same-key/different-semantic rejection, concurrent same-semantic convergence while the first transaction remains open, one durable document + one receipt, connection cleanup, receipt FORCE RLS, and append-only mutation rejection.

PostgreSQL 16 documents `pg_advisory_xact_lock` as an exclusive transaction-level advisory lock that waits when necessary and is automatically released at transaction end. The function is explicitly `VOLATILE`; PostgreSQL's function-volatility contract gives volatile functions a fresh snapshot for each query they execute under the ordinary Read Committed transaction model. That fresh post-lock lookup is what lets a waiting retry observe the first transaction's committed receipt rather than reinterpret a uniqueness error as success.

The future service adapter must keep this owner operation at PostgreSQL's ordinary Read Committed isolation unless a later migration supplies equivalent replay semantics for stronger isolation levels. Repeatable Read/Serializable establish longer-lived transaction snapshots; they must not be assumed to provide the same post-wait visibility. This is a contract constraint, not a reason to hold transactions open longer.

The expired IETF HTTPAPI `Idempotency-Key` Internet-Draft is non-normative background only. Its key principles—one client-generated key for retries and no key reuse with a different payload—are compatible with this design, but the draft expired on 2026-04-18 and is not cited as an active standard.

## Risks

Advisory-lock hash collisions can serialize unrelated commands, although they cannot merge their receipt state because the durable key remains tenant + exact idempotency key. The consequence is unnecessary waiting, not cross-command success.

The semantic digest is versioned as `orgmetra.document_record_persist_command.v1`. Any future change to governed command membership requires a new schema version and migration; silently changing digest membership would break deterministic replay interpretation.

A caller that abandons a connection mid-transaction relies on PostgreSQL rollback/connection cleanup. Acceptance therefore checks that concurrent test sessions terminate; production pooling/TLS/connection-recovery policy remains an operability concern at the future document-record service adapter.

A service that silently changes the transaction isolation level could invalidate the fresh-post-lock visibility assumption. Adapter acceptance must assert the supported isolation level before claiming retry convergence; stronger isolation requires an explicit successor design rather than accidental behavior.

## Follow-up

- Admit `tests/test_document_record_idempotency_postgres.sh` through the owner-neutral PostgreSQL Foundation registry once #310/#311 is reconciled with the document-record stack; do not add a feature-local workflow.
- Add the application/service adapter only after the `document_records` service boundary exists; it must map one external retry key to this transaction without reimplementing replay logic and must assert the supported transaction isolation.
- Re-run the full PostgreSQL acceptance on the exact protected-base head before changing this ADR from Proposed.
- Keep #308 return/destruction completion receipts separate: persistence idempotency proves creation/retry identity, not later retention or destruction completion.

## References

Jena, J., & Dalal, S. (2025, October 15). *The Idempotency-Key HTTP Header Field* (Internet-Draft draft-ietf-httpapi-idempotency-key-header-07, expired April 18, 2026). Internet Engineering Task Force. https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Advisory lock functions*. https://www.postgresql.org/docs/16/functions-admin.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Function volatility categories*. https://www.postgresql.org/docs/16/xfunc-volatility.html
