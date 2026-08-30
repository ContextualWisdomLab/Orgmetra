# PostgreSQL Employment-history read traceability

**Lifecycle status:** Active stacked PR #156 only. This document does not claim protected-`develop` integration.

## Buyer problem

PR #155 defines a customer-callable, purpose-bound Employment-history read but leaves persistence injected. Without a canonical adapter, an Orgmetra deployment cannot obtain that bounded history from normalized `employment_record` and `employment_record_version` truth without bespoke host code.

## Requirement-to-evidence matrix

| Requirement | Production boundary | Regression |
| --- | --- | --- |
| No DB access on invalid input | exact tenant/Person UUID and built-in UTC `known_at` validation before `connection_factory()` | invalid UUID/time cases assert zero connection calls |
| Database cannot mutate HR truth | `SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ ONLY` | SQL execution-order assertion |
| Tenant defense in depth | transaction-local `pg_catalog.set_config('orgmetra.tenant_record_id', ..., true)` before SELECT | exact SQL and parameter assertion |
| Explicit Employment/Person scope | fully qualified join between `public.employment_record_version` and `public.employment_record` with tenant/Person predicates | SQL contract assertions |
| Preserve system knowledge | half-open parent/version `recorded_from`/`recorded_to` predicates at `known_at` | future and closed-at-cutoff rows fail closed |
| Preserve business history | no effective-date filter; deterministic effective start/Employment/version ordering | returned typed dates and SQL ordering assertion |
| Canonical UTC | `AT TIME ZONE 'UTC'` projection and exact naive DB timestamp validation | string/aware/non-datetime timestamp regressions |
| Untrusted DB-API boundary | exact list result, exact tuple row shape, domain reconstruction | malformed collection/row/value regressions |
| Immutable typed result | tuple of `EmploymentHistoryRecord` values | empty and non-empty result regressions |
| Parent authority remains single owner | adapter accepts no purpose or authorization input | PR #155 performs authorization and service revalidation |

## Test-first chain

1. **Contract-only child head:** `1a8b9fb7` adds the adapter regressions while `orgmetra_people_api.postgres_employment_history` is absent.
2. **Expected RED:** local and exact hosted collection must fail with `ModuleNotFoundError` at that owning module boundary; predecessor or parent failures are not relabeled as adapter evidence.
3. **Implementation:** add the smallest adapter and package-root export, then rerun the full People API suite with exact statement and branch coverage.
4. **Database validation:** apply migration `0001_foundation_schema.sql` to an isolated PostgreSQL 16.14 database, seed anonymized tenant/Person/Employment facts, and execute the adapter through psycopg.
5. **Hosted evidence rule:** only the final exact current child head's dedicated workflow and applicable central checks may be used for advancement. Parent #155 evidence does not transfer.

## Security and data boundary

The adapter reads only Employment anchor identity/Person binding and Employment-version fields. It does not join organization, Job, Position, Assignment, compensation, candidate, performance, credential, prompt, or model-output data. Purpose-bound authorization-before-retrieval remains in the parent service; the adapter performs no mutation, audit/outbox write, or high-impact employment decision.

## Out of scope

- Employment-history HTTP/presentation integration; PR #155 owns that boundary.
- Employment mutation or correction workflows.
- Database migrations; the protected schema already owns these relations and RLS policies.
- Release, tag, publication, or protected-default-branch authority.
