# Employment-scoped base compensation traceability

## Truth classification

| State | Contract |
|---|---|
| Protected main | `compensation_record` is a legacy Person-scoped bitemporal relation with amount and currency but no Employment binding or pay-rate period. |
| Active PR #99 | `employment_base_compensation_record` binds one base-compensation anchor to one Employment; `employment_base_compensation_version` carries non-overlapping bitemporal amount/currency/rate-period truth; new legacy inserts fail closed. |
| Planned | Governed migration of historical legacy rows when an authoritative source supplies both Employment identity and pay-rate-period evidence; authoritative current-currency catalog validation; governed mutation/API materialization. |
| Out of scope | Payroll calculation, taxes, bonus/equity/allowances, total-rewards valuation, foreign-service table access, autonomous compensation decisions. |

## Requirement mapping

| Requirement | Evidence |
|---|---|
| Keep Person and Employment separate | New compensation anchor references `employment_record`, not `person_record`. |
| Support concurrent employments | PostgreSQL regression creates two Employment records for one Person and proves two independent compensation anchors/versions. |
| Preserve business and system time | Version rows carry independent `effective_*` and `recorded_*` intervals with a two-dimensional GiST exclusion. |
| Prevent history rewriting | Existing `protect_bitemporal_history()` is attached to both new relations; only closing an open `recorded_to` is accepted. |
| Tenant/context isolation | Composite tenant-qualified FK plus forced RLS policies on both relations; NOBYPASSRLS regression proves missing/cross-tenant contexts cannot observe Alpha rows. |
| Avoid ambiguous compensation facts | Base amount has explicit currency transport code and pay-rate period. New Person-scoped legacy inserts are rejected. |
| Avoid fabricated migration provenance | No automatic legacy backfill occurs because old rows lack Employment and pay-rate-period evidence. |
| Keep review and mutation authority separate | PR #48's compensation-change review packet remains a separate active lane; this slice adds only authoritative storage semantics. |

## Test-first evidence

- RED contract commit: `5dbd5ce10495a672868f17615bbf097ea7fe388d`.
- Exact RED quality head: `3a441b36522d52236208f5ec0ea3cfb2d382cc4e`.
- Hosted RED: Employment Compensation Core Quality run `32638352397`, job `97191386295`; exact checkout succeeded and the regression failed at the first owning boundary with `employment-scoped base-compensation relation is missing`.
- Root database repair: `0a1ace2d62d3443688a21bf724723eef9e2d514d`.
- First focused GREEN: Employment Compensation Core Quality run `32638412952`, job `97191541532` on the root-repair head.

Current-head hosted evidence must be refreshed after every later documentation, manifest, or gate change; predecessor runs are not merge evidence.

## Dedicated-writer boundary

No Keyverse, Naruon, contextual-orchestrator, psychometrics, migration-service, or other CWL dedicated-writer repository is mutated by this slice. No cross-service application-table SQL is introduced.