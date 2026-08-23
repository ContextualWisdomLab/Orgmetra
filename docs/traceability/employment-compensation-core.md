# Employment-scoped base compensation traceability

## Truth classification

| State | Contract |
|---|---|
| Protected main | `compensation_record` is a legacy Person-scoped bitemporal relation with amount and currency but no Employment binding or pay-rate period. |
| Active PR #99 | `employment_base_compensation_record` binds one base-compensation anchor to one Employment; `employment_base_compensation_version` carries non-overlapping bitemporal amount/currency/rate-period truth; new legacy inserts fail closed; new compensation system-recorded start time is database-authored. |
| Planned | Governed migration of historical legacy rows when an authoritative source supplies both Employment identity and pay-rate-period evidence; authoritative current-currency catalog validation; governed mutation/API materialization. |
| Out of scope | Payroll calculation, taxes, bonus/equity/allowances, total-rewards valuation, foreign-service table access, autonomous compensation decisions. |

## Requirement mapping

| Requirement | Evidence |
|---|---|
| Keep Person and Employment separate | New compensation anchor references `employment_record`, not `person_record`. |
| Support concurrent employments | PostgreSQL regression creates two Employment records for one Person and proves two independent compensation anchors/versions. |
| Preserve business and system time | Version rows carry independent `effective_*` and `recorded_*` intervals with a two-dimensional GiST exclusion. |
| Keep system time authoritative | Both new compensation relations default `recorded_from` to PostgreSQL transaction time and reject a caller-supplied value that differs from the current transaction timestamp; regressions cover anchor and version backdating attempts. |
| Prevent history rewriting | Existing `protect_bitemporal_history()` is attached to both new relations; only closing an open `recorded_to` is accepted. |
| Tenant/context isolation | Composite tenant-qualified FK plus forced RLS policies on both relations; NOBYPASSRLS regression proves missing/cross-tenant contexts cannot observe Alpha rows. |
| Avoid ambiguous compensation facts | Base amount has explicit currency transport code and pay-rate period. New Person-scoped legacy inserts are rejected. |
| Avoid fabricated migration provenance | No automatic legacy backfill occurs because old rows lack Employment and pay-rate-period evidence. |
| Keep review and mutation authority separate | PR #48's compensation-change review packet remains a separate active lane; this slice adds only authoritative storage semantics. |

## Test-first evidence

- Initial RED contract commit: `5dbd5ce10495a672868f17615bbf097ea7fe388d`.
- Initial exact RED quality head: `3a441b36522d52236208f5ec0ea3cfb2d382cc4e`.
- Initial hosted RED: Employment Compensation Core Quality run `32638352397`, job `97191386295`; exact checkout succeeded and the regression failed at the first owning boundary with `employment-scoped base-compensation relation is missing`.
- Initial root database repair: `0a1ace2d62d3443688a21bf724723eef9e2d514d`.
- First focused GREEN: Employment Compensation Core Quality run `32638412952`, job `97191541532` on that root-repair head.
- System-time hardening regression: `08a7422a96b5c9ed4aedd2eaaafd14c8e147e57b`. Its hosted run was superseded before execution and is not claimed as terminal RED evidence; source inspection proves the preceding migration accepted arbitrary `recorded_from`, while the regression encodes the required failure.
- System-time root repair: `1bb69b4cf9e392332828a5662f3a41b9e86238d0`; the following test-fixture adaptation removes caller-authored compensation timestamps and covers both anchor and version backdating attempts.

Current-head hosted evidence must be refreshed after every later code, documentation, manifest, or gate change; predecessor runs are not merge evidence.

## Dedicated-writer boundary

No Keyverse, Naruon, contextual-orchestrator, psychometrics, migration-service, or other CWL dedicated-writer repository is mutated by this slice. No cross-service application-table SQL is introduced.