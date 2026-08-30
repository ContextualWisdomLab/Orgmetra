# ADR 0156: Read Employment history from canonical PostgreSQL truth

- **Status:** Proposed on active stacked PR #156; not protected-main truth until integrated
- **Date:** 2026-08-30
- **Owners:** Orgmetra People API / HRIS persistence
- **Extends:** ADR 0003 (bitemporal HRIS data), ADR 0008 (purpose-bound PII authorization), ADR 0149 (Employment-history read contract), ADR 0155 (Employment-history HTTP read)

## Context

PR #155 exposes the customer-callable Employment-history HTTP boundary but keeps persistence injected. An integrated deployment still needs one canonical adapter for normalized `employment_record` and `employment_record_version` truth; otherwise each host could supply persistence code with different tenant or system-time semantics.

The adapter is not an authorization engine or a second source of truth. The parent People service authorizes before calling it and revalidates its typed output before disclosure. The existing schema owns Employment identity, Person binding, bitemporal version facts, tenant RLS, and immutable-history guards.

## Decision

Add `PostgresEmploymentHistoryReadPort` as the PostgreSQL implementation of the `EmploymentHistoryReadPort` protocol.

The adapter:

1. validates exact operational tenant/Person UUIDs and an exact built-in UTC `known_at` before acquiring a connection;
2. opens one `READ COMMITTED, READ ONLY` transaction and sets the transaction-local tenant context before the protected query;
3. joins only Orgmetra-owned `employment_record_version` to its `employment_record` anchor, preserving Person scope without joining another bounded context's application tables;
4. applies explicit tenant, Person, parent-recorded, and version-recorded half-open predicates;
5. projects recorded timestamps with `AT TIME ZONE 'UTC'`, accepts only exact naive UTC DB projections, and attaches built-in UTC after validation; and
6. treats DB-API output as untrusted by checking the default list collection, exact tuple row shape, domain reconstruction, requested target identity, and knowledge-cutoff visibility before returning an immutable tuple.

Purpose-bound field authorization remains in the parent service. This adapter performs no mutation, audit/outbox write, foreign-service call, disclosure, or high-impact employment decision.

## Consequences

### Positive

- The Employment-history application contract can use canonical normalized PostgreSQL truth without host-specific persistence code.
- Read-only transaction mode, explicit predicates, and tenant context provide layered database scope controls.
- Person, Employment identity, and Employment-version history remain separate while business-effective time stays distinct from system-recorded visibility.
- Exact DB timestamp validation prevents driver/session timezone behavior from changing evidence meaning.

### Trade-offs

- The adapter is PostgreSQL/DB-API specific and intentionally requires the default tuple-row contract.
- Database RLS and bitemporal constraints still require independent PostgreSQL tests; this adapter does not claim SQL predicates replace authorization or schema constraints.
- The parent service must continue to revalidate rows before serialization.

## Verification

The contract-first child test head `1a8b9fb7` fails during collection while the adapter module is absent. The final child must show exact-current-head full People API coverage, invalid-input zero-connection behavior, transaction ordering, explicit SQL scope, UTC projection, malformed-row rejection, target/visibility rechecks, immutable results, a real PostgreSQL 16.14 seeded-database validation, and a clean checkout. Parent #155 evidence does not transfer.

The implementation follows PostgreSQL transaction access-mode guidance and the existing protected Orgmetra RLS contract. These controls are defense in depth and do not authorize a merge or protected-main representation while this PR is Draft or central gates lack authoritative verdicts.
