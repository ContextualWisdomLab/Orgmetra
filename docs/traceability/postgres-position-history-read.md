# PostgreSQL Position-history read traceability

**Lifecycle status:** Proposed on active stacked PR #153 only. This document does not claim protected-`develop` integration.

## Buyer problem

PR #152 defines an authorized Position-history read but leaves persistence injected. Without a canonical adapter, an Orgmetra deployment cannot obtain that bounded history from normalized `position_record` and `position_record_version` truth without bespoke host code.

## Requirement-to-evidence matrix

| Requirement | Production boundary | Regression |
| --- | --- | --- |
| No DB access on invalid input | exact tenant/Position UUID and built-in UTC `known_at` validation before `connection_factory()` | invalid UUID/time cases assert zero connection calls |
| Stable request identity | tenant/Position UUIDs are reduced to built-in integer scalar authority before connection acquisition and fresh UUID views are used for DB parameters | a connection factory that mutates retained caller UUID aliases cannot change tenant GUC or SELECT target |
| Stable DB capability | `connection_factory` is held in tuple payload, not a writable instance slot | `object.__setattr__` cannot replace the accepted capability |
| Real transaction context | acquired connection must expose exact `autocommit is False` before `cursor()` | `True`, missing/`None`, numeric `0`, and string `"false"` modes fail before cursor access |
| Database cannot mutate HR truth | only after non-autocommit proof, execute `SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ ONLY` | execution-order and autocommit regressions |
| Tenant defense in depth | transaction-local `pg_catalog.set_config('orgmetra.tenant_record_id', ..., true)` before SELECT in the same proven transaction context | exact SQL and detached tenant parameter assertion |
| Explicit Position scope | fully qualified join between `public.position_record_version` and `public.position_record` with tenant/Position predicates | SQL contract assertions |
| Preserve system knowledge | half-open parent/version `recorded_from`/`recorded_to` predicates at `known_at` | future and closed-at-cutoff rows fail closed |
| Preserve business history | no effective-date filter; deterministic effective start/version ordering | returned typed dates and SQL ordering assertion |
| Canonical UTC | `AT TIME ZONE 'UTC'` projection and exact naive DB timestamp validation | string/aware/non-datetime timestamp regressions |
| Untrusted DB-API boundary | exact list result, exact tuple row shape, parent record reconstruction | malformed collection/row/value regressions |
| Immutable typed result | tuple of scalar-backed `PositionHistoryRecord` values | empty/non-empty result and parent retained-authority regressions |
| Parent authority remains single owner | adapter accepts no purpose or authorization input | PR #152 performs authorization and service revalidation |
| Repository acceptance owner | consolidated Foundation CI after descendant reaches a protected-parent/`develop` integration lane | feature-local pre-consolidation workflow is absent from the current stack |

## Test-first and restack chain

1. **Original contract-only child head:** `bf93924e` added adapter regressions while `orgmetra_people_api.postgres_position_history` was absent.
2. **Original implementation lineage:** the pre-consolidation branch added the adapter, tests, ADR/doctoring/traceability, and a feature-local quality workflow. Historical local/full-suite and isolated PostgreSQL results remain development evidence only and are not transferred to the current exact head.
3. **Parent reconciliation:** after #152 advanced to `616ed8c8a410e4dcdf4c31d293dfb082f7ce8297`, ordinary two-parent commit `a8edc7d2fa69842d4515def5c8a3e710ed4b4e2b` restacked #153 on that owner head without force push. The stale `.github/workflows/position-history-postgres-read-quality.yml` was deliberately not overlaid because protected #161 consolidated repository acceptance under Foundation CI.
4. **Retained-authority/transaction test-only head:** `800b783a74594a59f4c0d5dd819a6fce4fced4b8` adds regressions proving immutable connection capability, exact non-autocommit mode, rejection of unproven transaction modes, and detached request UUID authority before connection acquisition.
5. **Production repair:** `00d8f58d0863ef0d3270c7197d41856de3131e34` changes the adapter to a tuple-backed capability holder, snapshots request UUIDs to integer scalars, requires `autocommit is False` before cursor creation, uses fresh detached UUID views for tenant/query parameters, and compares returned scalar identity to the request snapshot.
6. **Fixture contract:** `d0a8b9b9b5e43bbc522b97c921a1d67c51b5fb6c` makes the normal DB-API fixture explicitly non-autocommit rather than relying on an unspecified connection mode.
7. **ADR currentization:** `6d0e185fdbce6d3d5b6a49c70353bcb0809830c2` records transaction proof, immutable capability ownership, UUID detachment, and consolidated workflow ownership.

No hosted RED or GREEN is claimed for the new stacked heads merely because PR-triggered Foundation runs are absent. Once its parent lineage is protected and #153 can target `develop`, the exact final child head must reacquire Foundation/Security/SAST/CodeQL and qualifying independent review. Parent, predecessor, manual, or historical isolated-PostgreSQL evidence does not transfer.

## Security and data boundary

The adapter reads only Position anchor lineage and Position-version fields. It does not join Person, Employment, Assignment, compensation, candidate, performance, credential, prompt, or model-output data. Purpose-bound authorization-before-retrieval remains in the parent service; the adapter performs no mutation, audit/outbox write, or high-impact employment decision.

The database transaction is intentionally narrow: connection acquisition → explicit non-autocommit proof → read-only/tenant-context setup → bounded SELECT/fetch → context exit. Authorization and other potentially long-running work do not execute while this adapter transaction is open.

## Out of scope

- Position-history HTTP/presentation integration (#154).
- Position mutation or correction workflows.
- Assignment/Employment history joins.
- Database migrations; the protected schema already owns these relations and RLS policies.
- Release, tag, publication, or protected-default-branch authority.

Any later descendant must preserve these boundaries and consume this adapter through its owner stack rather than copying its source.
