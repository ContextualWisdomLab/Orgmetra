# ADR 0309: Idempotent document-record persistence under uncertain outcomes

## Status

Proposed. This ADR describes the stacked implementation for issue #309 and is not protected-`develop` truth until its prerequisites and this change integrate normally.

## Problem

ADR 0107 and migrations 0021–0023 make one `document_record` immutable, tenant-scoped, evidence-bound, unique-key JSON safe, and byte-canonical. Those invariants prevent duplicate durable identities from being silently accepted, but a uniqueness error is not an idempotent result contract.

A caller can lose the response after PostgreSQL commits. If it retries the same logical persistence command, the owner must distinguish that retry from a different command that reused the same key. Treating a generic unique violation as success would conflate those cases; generating new audit/outbox references on every retry would also make one logical command appear as multiple durable events.

The lock boundary must remain short. Document parsing, OCR, model inference, artifact transfer, or any other network/compute work is not permitted inside the database transaction used for retry arbitration. Tenant identity must also be verified before the function acquires any advisory lock; RLS at the eventual table write is too late because advisory locks are database-global coordination state rather than row-scoped state.

The callable database boundary must also preserve the same invariant. A `SECURITY INVOKER` function cannot be treated as an execute-only persistence capability if a future service principal also needs direct `SELECT`/`INSERT` on the underlying tables to make the function work: those privileges would let that principal bypass the replay receipt and call path entirely.

## Decision

`document_records` owns a tenant-scoped `document_record_persist_receipt` and the `persist_document_record_once(...)` transaction boundary.

The command accepts one opaque, purpose-bound idempotency key of the form `document-record-persist-<uuid-v4>`. It computes a server-side SHA-256 semantic digest over the complete governed persistence command, excluding only PostgreSQL-owned result time. The key itself is not part of the semantic digest; it identifies a retry family rather than changing document semantics.

PostgreSQL grants `EXECUTE` on newly created functions to `PUBLIC` by default. Migration 0024 revokes that ambient grant and establishes two reserved NOLOGIN/NOBYPASSRLS roles after a fail-before-mutation collision preflight. `orgmetra_document_persistence_owner` owns `persist_document_record_once(...)` as a `SECURITY DEFINER` function and receives only schema usage plus the `SELECT`/`INSERT` and helper-function privileges required to implement the transaction. `orgmetra_document_persistence_executor` receives schema usage and `EXECUTE` on that exact function signature, but no direct document or receipt table privilege. The owner receives schema `CREATE` only long enough to complete the ownership handoff and loses it before the migration commits. Production login identities may acquire the executor capability only through explicit purpose-bound membership provisioning; migration execution requires authority to create the two fresh service-owned roles.

This is a narrow capability boundary, not a general preference for `SECURITY DEFINER`. The function pins `search_path`, the definer is NOLOGIN/NOBYPASSRLS and is not the table owner, FORCE RLS remains active, and direct DML remains unavailable to the externally assignable executor. The design follows the repository's existing hardened operator-recovery pattern rather than granting the application role both function execution and bypass-capable table DML.

After null-authoritative-field validation, the function requires `current_tenant_record_id()` to equal `p_tenant_record_id`. A mismatch fails with SQLSTATE `42501` before semantic digest computation, replay lookup, advisory-lock acquisition, or any durable write. This explicit owner check remains required even though both document and receipt tables use FORCE RLS: a privileged migration/test connection can bypass RLS, and an advisory lock can otherwise be acquired for another tenant before row security is evaluated.

Only after that tenant check does the function acquire `pg_advisory_xact_lock(hashtextextended(...))` over tenant + `document_records` namespace + key. The lock exists only until the current transaction ends. A same-key concurrent caller therefore waits until the first transaction commits or rolls back. No external I/O occurs while this lock is held.

After the lock:

- no receipt means the function inserts exactly one `document_record`, derives a receipt digest from the committed identity/result, and inserts one append-only receipt in the same transaction;
- an existing receipt with the same semantic digest returns the original document identity, document/audit/outbox references, semantic digest, receipt digest, and original database-owned `recorded_at`;
- an existing receipt with a different semantic digest fails closed before any second document write.

The receipt carries no document bytes, credentials, names, free-form HR content, compensation, ratings, or other duplicated Person/Employment truth. It stores only tenant identity, the opaque idempotency key, semantic digest, committed document identity, receipt digest, and system time. It is FORCE-RLS protected and append-only, including TRUNCATE protection.

The implementation adds a tenant-qualified unique key to `document_record` so the receipt can use a composite `(tenant_record_id, document_record_id)` foreign key. This preserves the bounded-context invariant that a receipt cannot point at a document from another tenant even if an otherwise valid UUID is supplied.

## Alternatives considered

**Return success on a unique violation.** Rejected. A uniqueness violation does not prove that the existing row came from the same semantic command.

**Retry heuristics in `talent_acquisition` or another consumer.** Rejected. Persistence replay truth belongs to `document_records`; copying mutable owner logic would create two authorities.

**Rely on PostgreSQL's default `PUBLIC` function EXECUTE privilege.** Rejected. `persist_document_record_once(...)` is a write capability for restricted HR metadata, not a cluster-wide utility. Authentication and tenant checks inside the function do not replace least-privilege admission to the function itself, and ambient defaults must not silently widen the callable persistence surface.

**Keep the function `SECURITY INVOKER` and grant a service principal the table privileges it needs.** Rejected. The service principal would then be able to insert or read persistence tables directly and bypass the exact idempotency/replay boundary that the function is intended to own. Execute-only admission requires a separate hardened function owner with the table privileges and a caller role with no direct DML.

**Make the migration or login role the `SECURITY DEFINER` owner.** Rejected. A login or cluster-powerful migration role would make function compromise materially broader. The dedicated owner is NOLOGIN, NOBYPASSRLS, denied schema CREATE after handoff, and receives only the object privileges required by this one capability.

**Rely on table RLS to reject a mismatched tenant after lock acquisition.** Rejected. Row security protects table access, not database-global advisory-lock ownership. A mismatched request must be rejected before it can coordinate on another tenant's retry key, and privileged maintenance connections must not silently bypass the bounded-context tenant invariant.

**Hold an explicit transaction open around upstream document processing.** Rejected. That would create the long-lived idle/lock behavior this architecture forbids. All expensive work must finish before entering `persist_document_record_once(...)`.

**Rely only on `INSERT ... ON CONFLICT`.** Rejected for this increment because the owner must compare a complete semantic digest and return the original result as one contract, not merely suppress a duplicate insert. The transaction-scoped advisory lock follows the already-protected People mutation pattern and makes the replay branch explicit.

## Evidence and acceptance

`tests/test_document_record_idempotency_postgres.sh` exercises real PostgreSQL sessions. It proves same-key/same-semantic retry convergence, same-key/different-semantic rejection, concurrent same-semantic convergence while the first transaction remains open, one durable document + one receipt, connection cleanup, receipt FORCE RLS, and append-only mutation rejection. The same command is also executed first under UTC and then under Asia/Seoul; digest identity must remain unchanged because the owner function canonicalizes its temporal serialization to UTC. All supported calls now provide the tenant session context explicitly instead of relying on a privileged test owner. Because the function executes as the dedicated NOBYPASSRLS owner, this root also exercises the actual write path under the definer's restricted table grants and FORCE-RLS policy rather than succeeding only through the migration superuser.

`tests/test_document_record_idempotency_function_acl_postgres.sh` verifies both sides of the capability boundary. It requires the canonical owner and executor roles to be NOLOGIN/NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION/NOBYPASSRLS, requires the function to be `SECURITY DEFINER` and owned by `orgmetra_document_persistence_owner`, requires schema `CREATE` to be absent after handoff, and requires the owner to have only `SELECT`/`INSERT` on the document and receipt tables. The executor must have function `EXECUTE` and schema usage but zero direct `SELECT`/`INSERT`/`UPDATE`/`DELETE`/`TRUNCATE` privilege on those tables. A behavioral `SET ROLE` probe must be denied a direct table read while an EXECUTE-only function call reaches reviewed command validation. A separate run-unique unprivileged role must still fail at function authorization, proving `PUBLIC` EXECUTE remains revoked.

`tests/test_document_record_idempotency_tenant_context_postgres.sh` supplies a valid tenant-beta command while the session tenant is tenant-alpha and requires the explicit owner error `document persistence tenant context does not match requested tenant`. It also proves that the rejected attempt leaves zero beta document and receipt rows. This contract intentionally remains valid even when the Foundation database owner can bypass RLS, because the owner function itself must enforce the tenant boundary before advisory-lock acquisition.

PostgreSQL 16 documents `pg_advisory_xact_lock` as an exclusive transaction-level advisory lock that waits when necessary and is automatically released at transaction end. The function is explicitly `VOLATILE`; PostgreSQL's function-volatility contract gives volatile functions a fresh snapshot for each query they execute under the ordinary Read Committed transaction model. That fresh post-lock lookup is what lets a waiting retry observe the first transaction's committed receipt rather than reinterpret a uniqueness error as success.

PostgreSQL 16 also documents that newly created functions receive `EXECUTE` for `PUBLIC` by default and recommends revoking that privilege in the same transaction when a function is not intended for every database role. Migration 0024 follows that boundary explicitly rather than relying on cluster-specific `ALTER DEFAULT PRIVILEGES` state. The dedicated owner/executor split then ensures the eventual application-facing principal can invoke the transaction without acquiring the underlying table privileges that would permit an alternate write path.

The owner function checks `transaction_isolation` before validating or mutating command state and fails closed unless it is `read committed`. `tests/test_document_record_idempotency_isolation_postgres.sh` enters a real `REPEATABLE READ` transaction and requires that isolation error before any command-field validation. Stronger isolation levels therefore cannot silently inherit semantics that depend on a fresh post-lock statement snapshot; a future successor must supply an explicit equivalent algorithm before relaxing this guard.

The expired IETF HTTPAPI `Idempotency-Key` Internet-Draft is non-normative background only. Its key principles—one client-generated key for retries and no key reuse with a different payload—are compatible with this design, but the draft expired on 2026-04-18 and is not cited as an active standard.

## Risks

Advisory-lock hash collisions can serialize unrelated commands, although they cannot merge their receipt state because the durable key remains tenant + exact idempotency key. The consequence is unnecessary waiting, not cross-command success. The explicit tenant-context guard prevents a caller from intentionally acquiring this coordination state for a different tenant through `persist_document_record_once(...)`.

The semantic digest is versioned as `orgmetra.document_record_persist_command.v1`. Any future change to governed command membership requires a new schema version and migration; silently changing digest membership would break deterministic replay interpretation.

A caller that abandons a connection mid-transaction relies on PostgreSQL rollback/connection cleanup. Acceptance therefore checks that concurrent test sessions terminate; production pooling/TLS/connection-recovery policy remains an operability concern at the future document-record service adapter.

The explicit Read Committed guard intentionally rejects a caller that promotes this one operation to Repeatable Read or Serializable without a successor design. That is a compatibility boundary, not an invitation to weaken isolation elsewhere: the future adapter must scope transaction policy to this documented write contract.

The two reserved capability-role names are cluster-level security state. A pre-existing role with either name causes migration 0024 to fail before it mutates project objects rather than attempting to reuse unknown memberships or ACLs. This means deployment migration authority must include role creation, and operators must investigate rather than rename around a collision.

`SECURITY DEFINER` increases the importance of the fixed search path, narrow owner grants, FORCE RLS, and the executor's lack of direct table access. Any future helper called from the function must be schema-qualified and must not expand the owner's privilege set without a corresponding executable ACL regression.

## Follow-up

- Admit `tests/test_document_record_idempotency_postgres.sh`, `tests/test_document_record_idempotency_function_acl_postgres.sh`, `tests/test_document_record_idempotency_isolation_postgres.sh`, and `tests/test_document_record_idempotency_tenant_context_postgres.sh` through the owner-neutral PostgreSQL Foundation registry once #310/#311 is reconciled with the document-record stack; do not add a feature-local workflow.
- Add the application/service adapter only after the `document_records` service boundary exists. Its authenticated login role must obtain purpose-bound membership in `orgmetra_document_persistence_executor`; it must not receive direct table DML or reimplement replay logic.
- Re-run the full PostgreSQL acceptance on the exact protected-base head before changing this ADR from Proposed.
- Keep #308 return/destruction completion receipts separate: persistence idempotency proves creation/retry identity, not later retention or destruction completion.

## References

Jena, J., & Dalal, S. (2025, October 15). *The Idempotency-Key HTTP Header Field* (Internet-Draft draft-ietf-httpapi-idempotency-key-header-07, expired April 18, 2026). Internet Engineering Task Force. https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Advisory lock functions*. https://www.postgresql.org/docs/16/functions-admin.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Function volatility categories*. https://www.postgresql.org/docs/16/xfunc-volatility.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Privileges*. https://www.postgresql.org/docs/16/ddl-priv.html
