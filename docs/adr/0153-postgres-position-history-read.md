# ADR 0153: Read Position history from canonical PostgreSQL truth

- **Status:** Proposed on active stacked PR #153; not protected `develop` truth until integrated
- **Date:** 2026-08-30
- **Owners:** Orgmetra People API / HRIS persistence
- **Extends:** ADR 0003 (bitemporal HRIS data), ADR 0008 (purpose-bound PII authorization), ADR 0152 (Position-history read contract)

## Context

PR #152 defines the buyer-facing, purpose-bound Position-history read but intentionally injects its persistence port. An integrated application still needs a canonical adapter for normalized `position_record` and `position_record_version` truth; otherwise each deployment would supply bespoke persistence code and could silently widen the read.

The adapter is not a second authorization engine or source of truth. The parent People service authorizes before calling it and revalidates its typed output before disclosure. The existing schema already owns Position/Job lineage, bitemporal version facts, tenant RLS, and immutable-history guards.

A PostgreSQL statement that says `SET TRANSACTION ... READ ONLY` is not sufficient proof by itself. The adapter also uses transaction-local tenant context (`set_config(..., true)`), so both controls require an actual non-autocommit transaction. Likewise, validating a connection factory and then retaining it in a writable instance slot would create a checked-versus-used capability gap, and retaining caller UUID objects after validation would allow alias mutation between validation and SQL execution.

## Decision

Add `PostgresPositionHistoryReadPort` as the canonical PostgreSQL implementation of the `PositionHistoryReadPort` protocol introduced by PR #152.

The adapter:

1. validates exact operational tenant/Position UUIDs and an exact built-in UTC `known_at` before acquiring a connection;
2. immediately reduces tenant and Position UUIDs to exact built-in integer scalar authority, then reconstructs fresh UUID views only for DB-API parameter contracts;
3. stores the validated `connection_factory` in immutable tuple payload rather than a writable dataclass slot and uses that exact capability for the read;
4. requires the acquired connection to prove `autocommit is False` before cursor creation; absent, truthy, numeric-zero, string, or otherwise unproven modes fail closed;
5. only after that proof executes `SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ ONLY`, sets transaction-local tenant context, and runs the protected SELECT inside the same connection context;
6. joins only `public.position_record_version` to its Orgmetra-owned `public.position_record` anchor, preserving Job and organization lineage without Person, Employment, Assignment, compensation, candidate, performance, credential, or decision joins;
7. applies explicit tenant, Position, parent-recorded, and version-recorded half-open predicates;
8. projects recorded timestamps with `AT TIME ZONE 'UTC'`, accepts only exact naive UTC DB projections, and attaches built-in UTC after validation;
9. treats DB-API output as untrusted by checking the default list collection, exact tuple row shape, parent-record integrity, requested target identity, and knowledge-cutoff visibility before returning an immutable tuple;
10. compares returned tenant/Position scalar authority to the detached request scalars, so post-validation mutation of caller UUID aliases cannot change the authorized query target.

Purpose-bound field authorization remains in the parent service. This adapter performs no mutation, audit/outbox write, foreign-service call, decision, or disclosure.

## Workflow ownership

Repository workflow consolidation on protected `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f` makes Foundation CI the repository acceptance owner. The pre-consolidation `.github/workflows/position-history-postgres-read-quality.yml` is not carried forward by the semantic restack. Stacked feature heads are not treated as GREEN merely because their parent or predecessor once passed a feature-local workflow.

## Consequences

### Positive

- The Position-history application contract can use canonical normalized PostgreSQL truth without host-specific persistence code.
- The read-only and transaction-local tenant controls are only attempted after the connection proves a non-autocommit transaction mode.
- The connection capability used by the adapter cannot be swapped through ordinary or `object.__setattr__` instance mutation after construction.
- Caller-retained UUID aliases cannot change tenant/Position SQL parameters after validation.
- Explicit predicates and forced-RLS tenant context provide layered database scope controls.
- Position, Job, and Assignment remain separate concepts, and business-effective history remains distinct from system-recorded visibility.
- Exact DB timestamp validation prevents driver/session timezone behavior from silently changing evidence meaning.

### Trade-offs

- The adapter is PostgreSQL/DB-API specific and intentionally requires the default tuple-row contract.
- Compatible connection objects must expose `autocommit` and prove it with the exact built-in value `False`; implicit or driver-specific lookalikes are rejected at this high-trust boundary.
- Database RLS and bitemporal constraints still require independent PostgreSQL tests; this adapter does not claim that SQL predicates replace authorization or schema constraints.
- The parent service must be integrated first and must continue to revalidate rows before serialization.

## Verification

The original contract-first child head `bf93924e` established the adapter boundary while the module was absent. Historical local and isolated PostgreSQL checks from the pre-consolidation branch remain development evidence only; they are not current exact-head merge evidence.

After PR #152 moved to its protected-workflow-consolidated and retained-authority-hardened head, ordinary two-parent reconciliation `a8edc7d2fa69842d4515def5c8a3e710ed4b4e2b` restacked the adapter without force push and deliberately omitted the stale feature-local quality workflow. Test-only head `800b783a74594a59f4c0d5dd819a6fce4fced4b8` added four contracts: immutable connection capability, explicit rejection of `autocommit=True`, rejection of unproven transaction modes, and request UUID alias detachment before connection acquisition. Production repair `00d8f58d0863ef0d3270c7197d41856de3131e34` implements those boundaries, and `d0a8b9b9b5e43bbc522b97c921a1d67c51b5fb6c` updates the ordinary test fixture to state its non-autocommit contract explicitly.

Because #153 remains stacked on a feature branch, no hosted RED or GREEN is inferred from the absence of PR-triggered Foundation runs. The final descendant must first inherit an integrated/protected parent, retarget to `develop`, and then obtain fresh exact-current-head Foundation/Security/SAST/CodeQL evidence plus qualifying independent review. Parent #152 and predecessor evidence do not transfer.
