# Audit evidence review traceability

## Protected-main truth

`develop@9e3e4847510e1e612b48474ba42b177b8ed824df` already owns immutable, PII-minimized audit/outbox persistence: `AuditOutboxEvent` produces deterministic CloudEvents-compatible canonical JSON and SHA-256, and `database/migrations/0003_audit_outbox_persistence.sql` stores it in forced-RLS `audit_event_record` with append-only mutation guards. Protected main does not yet contain this review package.

## Active-PR truth

PR #102 adds the transport-neutral `orgmetra-audit-evidence-review` boundary. The package requires authorization before store access; exact authorization scope; bounded system-recorded interval and result count; exact runtime trust primitives; SHA-256 and canonical-JSON revalidation; row/event/tenant binding; in-window tenant-only rows; and strict `(recorded_at, audit_event_record_id)` order. The package contains no HR application-table query and no employment-decision authority.

The first contract head `592cd8f097cb1d45cd901b85f542b590f9ebb546` intentionally had no production package and is the test-first predecessor. Its workflows were queued before follow-up commits, so it is not claimed as terminal hosted RED evidence and no predecessor status is transferred.

Fresh self-review then found a distinct privacy-integrity defect after the first implementation: canonical JSON plus a recomputed digest could carry additional top-level HR data or extra nested `data` fields because read-time verification checked the digest, CloudEvents version, event id and tenant but not the exact existing PII-minimized envelope shape. RED regression `1aa81b250669373ffd63c2b398925773c6cf967c` requires both widened shapes to fail closed and also requires malformed unencodable text to become a stable validation failure. Root repair `fb668be543d93c2bc7a1d0a930d5f889a916fd7b` binds read-time verification to the exact protected-main audit key sets and hashes a single verified UTF-8 byte sequence.

A second runtime-integrity self-review found that Python frozen dataclasses can still be rewritten with `object.__setattr__` after successful construction. Without boundary revalidation, a once-valid query could have its limit widened, a once-valid authorization could have `permitted` rewritten to a truthy non-boolean, and a once-valid persisted row could have both canonical JSON and digest replaced after construction. RED regression `b9385dbe9c9501dd1748cca6261c4d4c118ac1dd` fixes those attack paths as acceptance tests. Root repair `5005c9f58c3f35c6a08b8134362478418d011bcc` reconstructs live query, authorization, and row fields through their governed constructors and returns detached verified row snapshots, so authorization/store access and returned evidence never rely on a merely once-valid mutable Python object.

Current implementation must be evaluated only on its own exact head and applicable workflows.

## Planned host adapters

A PostgreSQL reader may later implement `AuditEvidenceRowReader` using the existing Orgmetra audit relation, a least-privileged `NOSUPERUSER NOBYPASSRLS` role, read-only transaction, exact tenant context, parameterized half-open recorded-time window, deterministic ordering and authorized limit. A customer-facing audit UI may consume the resulting verified page through an application API. These are planned until separately implemented and tested.

## Out of scope

This PR does not create a second audit store, copy HR values into an index, query another service's application tables, mutate any dedicated-writer dependency repository, authorize employment decisions, provide SIEM correlation, or claim NIST/SOC 2 certification.
