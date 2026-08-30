# ADR 0153: Read Position history from canonical PostgreSQL truth

- **Status:** Proposed on active stacked PR #153; not protected-main truth until integrated
- **Date:** 2026-08-30
- **Owners:** Orgmetra People API / HRIS persistence
- **Extends:** ADR 0003 (bitemporal HRIS data), ADR 0008 (purpose-bound PII authorization), ADR 0152 (Position-history read contract)

## Context

PR #152 defines the buyer-facing, purpose-bound Position-history read but intentionally injects its persistence port. An integrated application still needs a canonical adapter for normalized `position_record` and `position_record_version` truth; otherwise each deployment would supply bespoke persistence code and could silently widen the read.

The adapter is not a second authorization engine or source of truth. The parent People service authorizes before calling it and revalidates its typed output before disclosure. The existing schema already owns Position/Job lineage, bitemporal version facts, tenant RLS, and immutable-history guards.

## Decision

Add `PostgresPositionHistoryReadPort` as the canonical PostgreSQL implementation of the `PositionHistoryReadPort` protocol introduced by PR #152.

The adapter:

1. validates exact operational tenant/Position UUIDs and an exact built-in UTC `known_at` before acquiring a connection;
2. opens one `READ COMMITTED, READ ONLY` transaction and sets the transaction-local tenant context before the protected query;
3. joins only `public.position_record_version` to its Orgmetra-owned `public.position_record` anchor, preserving Job and organization lineage without Person, Employment, Assignment, compensation, candidate, performance, credential, or decision joins;
4. applies explicit tenant, Position, parent-recorded, and version-recorded half-open predicates;
5. projects recorded timestamps with `AT TIME ZONE 'UTC'`, accepts only exact naive UTC DB projections, and attaches built-in UTC after validation;
6. treats DB-API output as untrusted by checking the default list collection, exact tuple row shape, parent-record integrity, requested target identity, and knowledge-cutoff visibility before returning an immutable tuple.

Purpose-bound field authorization remains in the parent service. This adapter performs no mutation, audit/outbox write, foreign-service call, decision, or disclosure.

## Consequences

### Positive

- The Position-history application contract can use canonical normalized PostgreSQL truth without host-specific persistence code.
- Read-only transaction mode, explicit predicates, and forced-RLS tenant context provide layered database scope controls.
- Position, Job, and Assignment remain separate concepts, and business-effective history remains distinct from system-recorded visibility.
- Exact DB timestamp validation prevents driver/session timezone behavior from silently changing evidence meaning.

### Trade-offs

- The adapter is PostgreSQL/DB-API specific and intentionally requires the default tuple-row contract.
- Database RLS and bitemporal constraints still require independent PostgreSQL tests; this adapter does not claim that SQL predicates replace authorization or schema constraints.
- The parent service must be integrated first and must continue to revalidate rows before serialization.

## Verification

The contract-first child test head `bf93924e` fails during collection while the adapter module is absent. The final child must show exact-current-head full People API coverage, invalid-input zero-connection behavior, transaction ordering, explicit SQL scope, UTC projection, malformed-row rejection, target/visibility rechecks, immutable results, and a clean checkout. Parent #152 evidence and reviews do not transfer.

The implementation follows PostgreSQL 18 transaction access-mode guidance and the existing protected Orgmetra RLS contract. These controls are defense in depth and do not authorize a merge or protected-main representation while this PR is Draft or central gates lack authoritative verdicts.

