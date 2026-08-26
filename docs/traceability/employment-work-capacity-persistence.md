# Employment work-capacity persistence traceability

## Truth status

- **Protected/default-branch truth:** `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` does not yet ship authoritative Employment work-capacity persistence.
- **Parent active-PR truth:** #103 owns non-authorizing human-reviewed work-capacity evidence at exact head `645d2f3b2db10e2bdfbe60422837a5986d8f39f8`.
- **This active-PR truth:** #128 owns the durable application/persistence boundary plus forward-chain hardening. It is a dependency-first Draft and is not shipped product truth.
- **Out of scope:** payroll calculation, compensation mutation, statutory leave classification, scheduling, disability/medical case data, Assignment mutation, candidate decisions, retroactive replay/correction, or foreign-service table access.

## Requirement-to-evidence map

| Requirement | Implementation boundary | Regression evidence |
|---|---|---|
| Separate Employment capacity from Assignment allocation | `employment_work_capacity_record` / `employment_work_capacity_version` | focused PostgreSQL happy path plus prohibited-column checks |
| One durable capacity anchor per tenant-qualified Employment | unique `(tenant_record_id, employment_record_id)` | second/later applications reuse the same anchor |
| Preserve business and system time | `effective_on` plus `recorded_from`/`recorded_to` | business-date resolver and immutable history checks |
| Do not invent pre-bootstrap history | resolver returns no row before first `effective_on` | `before_first == none` regression |
| Match later reviews to current authoritative truth | latest visible effective point is compared with reviewed current ratio | mismatched-current adversarial application must fail |
| Prevent retroactive downstream-chain corruption | migration 0032 locks the same tenant/Employment chain and requires `effective_on` after the latest visible point | dedicated fresh-database regression attempts Sep-15 insertion after Sep-1/Oct-1 truth and requires fail-closed with October truth unchanged |
| Bind exact parent review evidence | raw review JSON SHA-256, exact key set and normalized field comparison | forged review digest and mismatched scope regressions |
| Human review and actor separation | parent review state plus requester/reviewer/applier separation | reviewer-as-applier adversarial regression |
| Purpose/reason/evidence versioning | fixed application purpose, controlled reason and evidence version 1 | persisted-state and review-shape checks |
| Immutable audit/outbox correlation without cross-service SQL | opaque review-audit/application-audit/application-outbox references and envelope digests | format constraints; no foreign application-table query in migration |
| Database-owned system time | `transaction_timestamp()` defaults and insert guards | caller has no application parameter for system-recorded time; row guard requires transaction time |
| Concurrency safety | transaction advisory lock on tenant + Employment before current-state and forward-chain validation | application and migration 0032 use the same lock key; future concurrency tests must preserve this invariant |
| Tenant isolation | FORCE RLS policies using transaction-local tenant context | `NOSUPERUSER NOBYPASSRLS` reader sees own rows and zero foreign rows |
| No broad mutation authority | `PUBLIC` execute revoked on authoritative apply/resolve functions | `has_function_privilege('public', ...) = false` regression |
| Correction not rewrite | only database-time closure of `recorded_to` is allowed | UPDATE/DELETE/TRUNCATE adversarial regressions; retroactive business correction requires a separate replay boundary |

## Buyer-visible behavior

A buyer may resolve contracted Employment capacity at a business date and a system-knowledge cutoff after purpose-bound host authorization. The result is Employment truth, not a performance rating, fitness-for-work judgment, pay amount, leave classification, or scheduling instruction. Customer-facing surfaces should explain the next action: review downstream Assignment allocation and compensation/payroll impacts through their own authoritative boundaries before those domains are changed.

Normal reviewed changes move the authoritative effective-point chain forward. If HR must correct an earlier business-effective point after later points already exist, this boundary refuses the mutation instead of silently invalidating downstream review premises. A future replay/correction operation must re-prove every affected later point and emit new immutable evidence.

## Merge/release conditions

Focused stack evidence never transfers from #103 or into a later restack. After #103 actually integrates, retarget #128 to fresh `develop`, independently resolve the new base tip, reconcile migration/provenance inventories, and rerun every applicable Foundation/People/Workforce/Job-Analysis/SAST/Security/Recovery/coverage/package/central gate on one exact child head. No merge or release is authorized by this document.