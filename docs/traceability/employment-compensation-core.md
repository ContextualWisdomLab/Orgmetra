# Employment-scoped base compensation traceability

## Truth classification

| State | Contract |
|---|---|
| Protected main | `compensation_record` is a legacy Person-scoped bitemporal relation with amount and currency but no Employment binding or pay-rate period. |
| Active PR #99 | `employment_base_compensation_record` binds one base-compensation anchor to one Employment; `employment_base_compensation_version` carries non-overlapping bitemporal amount/currency/rate-period truth; new legacy inserts fail closed; `recorded_from` is fixed to PostgreSQL transaction time, new rows must start with `recorded_to IS NULL`, and a later closure is accepted only when the supplied `recorded_to` equals PostgreSQL transaction time. Reserved UUID sentinels, `NaN` compensation, row rewrites, deletes, and table-wide TRUNCATE are rejected. |
| Planned | Governed migration of historical legacy rows when an authoritative source supplies both Employment identity and pay-rate-period evidence; authoritative current-currency catalog validation; governed mutation/API materialization. |
| Out of scope | Payroll calculation, taxes, bonus/equity/allowances, total-rewards valuation, foreign-service table access, autonomous compensation decisions. |

## Requirement mapping

| Requirement | Evidence |
|---|---|
| Keep Person and Employment separate | New compensation anchor references `employment_record`, not `person_record`. |
| Support concurrent employments | PostgreSQL regression creates two Employment records for one Person and proves two independent compensation anchors/versions. |
| Preserve business and system time | Version rows carry independent `effective_*` and `recorded_*` intervals with a two-dimensional GiST exclusion. |
| Keep system time authoritative | Both new compensation relations default `recorded_from` to PostgreSQL transaction time, reject a caller-supplied start that differs from the current transaction timestamp, and reject non-NULL `recorded_to` on INSERT. BEFORE UPDATE close guards do not author the value; they accept a changed `recorded_to` only when it equals PostgreSQL transaction time. Regressions prove arbitrary backdating, pre-closed insertion, and arbitrary future/manual closure fail closed while a transaction-time closure succeeds. |
| Reject reserved durable identities | Both compensation primary keys use the canonical `is_operational_uuid(...)` constraint; review-driven regressions reject RFC 9562 Nil and Max sentinels. |
| Keep compensation numeric truth finite enough for governed comparison | The amount constraint rejects negative values and PostgreSQL `NaN`; review-driven regression proves `NaN` cannot be persisted as a non-negative amount. |
| Prevent history rewriting or table-wide erasure | Existing `protect_bitemporal_history()` is attached to both new relations; only closing an open `recorded_to` is accepted, and statement-level `BEFORE TRUNCATE` guards plus TRUNCATE privilege revocation prevent table-wide deletion from bypassing row-level history rules. |
| Tenant/context isolation | Composite tenant-qualified FK plus forced RLS policies on both relations; NOBYPASSRLS regressions independently prove anchor and version relations expose zero rows without context, only Alpha rows under Alpha context, and zero Alpha rows under Beta context. |
| Avoid ambiguous compensation facts | Base amount has explicit currency transport code and pay-rate period. New Person-scoped legacy inserts are rejected. |
| Avoid fabricated migration provenance | No automatic legacy backfill occurs because old rows lack Employment and pay-rate-period evidence. |
| Keep review and mutation authority separate | PR #48's compensation-change review packet remains a separate active lane; this slice adds only authoritative storage semantics. |
| Keep production database boundaries beginner-readable | Migration 0018 publishes `COMMENT ON FUNCTION` descriptions for the insert-time system clock guard, history-closure clock guard, TRUNCATE guard, and legacy-write rejection function. |
| Keep architecture decisions discoverable | ADR 0099 is registered in `docs/adr/README.md`, and the focused quality gate verifies the exact active-PR index entry. |

## Test-first evidence

- Initial RED contract commit: `5dbd5ce10495a672868f17615bbf097ea7fe388d`.
- Initial exact RED quality head: `3a441b36522d52236208f5ec0ea3cfb2d382cc4e`.
- Initial hosted RED: Employment Compensation Core Quality run `32638352397`, job `97191386295`; exact checkout succeeded and the regression failed at the first owning boundary with `employment-scoped base-compensation relation is missing`.
- Initial root database repair: `0a1ace2d62d3443688a21bf724723eef9e2d514d`.
- First focused GREEN: Employment Compensation Core Quality run `32638412952`, job `97191541532` on that root-repair head.
- System-time start hardening regression: `08a7422a96b5c9ed4aedd2eaaafd14c8e147e57b`. Its hosted run was superseded before execution and is not claimed as terminal RED evidence; source inspection proves the preceding migration accepted arbitrary `recorded_from`, while the regression encodes the required failure.
- System-time start root repair: `1bb69b4cf9e392332828a5662f3a41b9e86238d0`; the following test-fixture adaptation removes caller-authored compensation timestamps and covers both anchor and version backdating attempts.
- Manifest provenance repair after those changes: `5d076e6e88d8e3b593390dd0866943dbaa9dfbf5`.
- System-time closure regression: `bdd7b1274ba70ec29629ffbfbabb36bee1078348`. Its workflow was superseded by the immediate repair and is not claimed as terminal RED evidence; the pre-repair source used the generic history guard, which accepted any `recorded_to > recorded_from`.
- System-time closure root repair: `fa6f8ab9693e40948b9c62a269da41d2ab2e5769`. Employment Compensation Core Quality run `32639870101`, job `97195200896`, checked out that exact head and proved a caller-selected future `recorded_to` fails while `pg_catalog.transaction_timestamp()` closure succeeds; the full focused contract and clean-checkout step were GREEN.
- Canonical-doc regression `b34d03bf25699b0d1a12f91c5f78b9816b75b8b3` strengthened the focused gate so migration-backed compensation truth must appear in `docs/DATA_MODEL.md`, `docs/ERD.md`, `docs/TRACEABILITY.md`, and `CHANGELOG.md`. Its hosted workflow was later cancelled as superseded, so it is not terminal RED evidence, but its exact job reached the new assertion and failed specifically because the canonical docs omitted both compensation tables.
- Canonical-doc repair commits `085c69ce8e36296716c26b1da1f40589036bc36d`, `825ce793fa8d9403341d1508effb2c3cdb3e919f`, `dbb101514c168406b2ca21d6635a17b3a0fa58bd`, and `12bd2ccdfbbe358c8fc0293b5b552a3c65892f0a` align the data model, ERD, product traceability and changelog.
- Pre-closed system-evidence/RLS regression `7d5b8bc1a44f1f7690d0600062afc3570871d8ee` requires both anchor and version INSERT paths to reject caller-supplied `recorded_to` and independently exercises forced RLS on the version relation. The immediate root repair follows on the same canonical branch; any superseded or cancelled regression workflow remains non-passing evidence.
- Pre-closed system-evidence root repair `e05fded09e04f6f37df95c65c7f5dbb34556a1db` makes the shared INSERT system-time guard reject non-NULL `recorded_to` for both relations and adds beginner-readable public database-function comments without weakening the existing update-time guard.
- Review-driven integrity regression file `tests/test_employment_compensation_review_regressions_postgres.sh` was introduced at `1f2043a6cccc70ffa89d4af849adae0a0ab6de9a`; focused-gate commit `5d475ed5ae03ac397fd496f90ccdf7fe60cceb27` makes that regression and the ADR-index check executable on the exact candidate. The regression encodes rejection of reserved anchor/version identities, PostgreSQL `NaN`, and TRUNCATE. Root database repair `4154b3f78b1df47ae850961682e0fbb65f1abe11` adds the owning constraints and history-erasure guard; later commits align ADR/index/traceability.

Current-head hosted evidence must be refreshed after every later code, documentation, manifest, or gate change; predecessor runs are not merge evidence.

## Dedicated-writer boundary

No Keyverse, Naruon, contextual-orchestrator, psychometrics, migration-service, or other CWL dedicated-writer repository is mutated by this slice. No cross-service application-table SQL is introduced.
