# ADR 0148: Read Assignment history from canonical PostgreSQL truth

- **Status:** Proposed on active stacked PR #148; not protected-main truth until integrated.
- **Date:** 2026-08-29
- **Owners:** Orgmetra People API / HRIS persistence
- **Extends:** ADR 0003 (bitemporal HRIS data), ADR 0008 (purpose-bound PII authorization), ADR 0142 (Assignment-history read contract)

## Context

PR #142 defines the buyer-facing, purpose-bound employee Assignment-history read but intentionally injects its persistence port. Leaving that port without a canonical adapter means an integrated application still cannot obtain historical Assignment truth from Orgmetra's normalized `assignment_record` relation without supplying bespoke persistence code.

The adapter must not become a second authorization engine or a second source of truth. Purpose-bound authorization remains in the parent People service and runs before this adapter is called. The database already owns tenant-scoped Assignment facts and row-level-security policy; the adapter therefore needs a narrow read-only transaction, explicit tenant context, explicit target predicates, and a value-minimized projection.

PostgreSQL 18 documents `READ ONLY` as a transaction access mode that rejects ordinary table-changing statements. PostgreSQL row-security documentation also makes clear that row policies control which rows are visible to a query, while `FORCE ROW LEVEL SECURITY` applies those policies even to the table owner. Orgmetra uses those controls as defense in depth, not as a substitute for application authorization or explicit SQL scope.

## Decision

Add `PostgresAssignmentHistoryReadPort` as the canonical PostgreSQL implementation of the `AssignmentHistoryReadPort` protocol introduced by PR #142.

The adapter:

1. validates exact operational tenant/person UUIDs and an exact built-in UTC `known_at` before acquiring a connection;
2. opens a `READ COMMITTED, READ ONLY` transaction because one SQL statement is sufficient to reconstruct the requested recorded-time view;
3. sets transaction-local `orgmetra.tenant_record_id` before the protected query so existing forced RLS remains active as defense in depth;
4. queries only `public.assignment_record`, with explicit tenant, person, and half-open system-recorded predicates;
5. returns the full business-effective Assignment history visible at that system-knowledge cutoff rather than incorrectly filtering to one business date;
6. projects `recorded_from`/`recorded_to` through `AT TIME ZONE 'UTC'`, then attaches Python's built-in UTC timezone only after verifying PostgreSQL returned exact naive `datetime` values;
7. selects only the fields required by `AssignmentHistoryRecord` and never joins names, contacts, compensation, ratings, assessments, candidate data, credentials, prompts, or model output;
8. treats DB-API output as untrusted, revalidating row shape, canonical parent-record integrity, exact tenant/person scope, and half-open recorded-time visibility before returning an immutable tuple.

The parent service remains responsible for purpose-bound field authorization and for revalidating the returned records before disclosure. The adapter performs no mutation, audit/outbox write, cross-service SQL, candidate/worker inference, employment decision, or foreign-service call.

## Consequences

### Positive

- The P1 employee-profile Assignment-history contract can use Orgmetra's canonical normalized database without bespoke host persistence code.
- Read-only transaction mode and forced-RLS tenant context narrow database authority while explicit predicates make the intended scope reviewable in source.
- Business-effective time and system-recorded time remain separate; a `known_at` query cannot silently become a current-business-date query.
- UTC projection is deterministic and detached from driver/session timezone behavior before trust-bearing records reach the service layer.
- Parent purpose-bound authorization remains the only disclosure authority, avoiding duplicated policy engines.

### Trade-offs

- This adapter is PostgreSQL/DB-API specific and intentionally expects the default tuple-row contract rather than supporting arbitrary row factories.
- RLS configuration still requires independent database migration/role tests; this adapter does not claim that a SQL predicate alone proves tenant isolation.
- The adapter returns historical Assignment identifiers and relationships only to the parent service; whether any particular field is disclosed remains an authorization decision outside this adapter.

## Verification

PR #148 must preserve a genuine contract-first RED at the missing production-module boundary and then demonstrate, on one exact current head:

- exact 100% statement and branch coverage of the owned adapter;
- zero DB connection acquisition for invalid tenant/person/time inputs;
- read-only transaction mode and transaction-local tenant context before the protected query;
- explicit tenant/person/half-open recorded-time predicates and deterministic ordering;
- UTC projection and rejection of noncanonical DB timestamps;
- untrusted row shape, parent-record integrity, tenant/person, and recorded-visibility failure modes;
- immutable empty/non-empty results;
- clean checkout after focused tests.

Parent #142 must integrate first. Its checks and reviews do not transfer to this child.
