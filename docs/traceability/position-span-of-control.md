# Position span-of-control traceability

## State classification

- Protected `develop`: does **not** contain Position-to-Position reporting or span-of-control evidence at `9e3e4847510e1e612b48474ba42b177b8ed824df`.
- Parent active PR #94: owns governed bitemporal Position reporting at `3f67182bb3065f2fc8fd974bfdd75a390d8a8fdc`.
- Active child PR #133: owns descriptive Position span-of-control evidence. It is dependency-first active-PR truth only.
- Planned/out of scope here: persistence, authorized buyer presentation, organization-design simulation, target-span recommendations, staffing actions and employment decisions.

## Requirements to evidence

| Requirement | Implementation | Regression / evidence |
|---|---|---|
| Count Position seats, not workers | `build_position_span_of_control_snapshot()` consumes only `PositionReportingSnapshot` | `test_span_snapshot_counts_direct_reporting_positions_only` and canonical JSON PII assertions |
| Preserve bitemporal coordinate | tenant/effective/system fields copied from exact parent snapshot | noncanonical parent-coordinate regressions |
| Resist forged direct parent construction | exact runtime, UUID, tuple, uniqueness, self-edge and cycle revalidation | hostile graph/container/runtime regressions |
| Deterministic structural evidence | UUID-sorted `span_by_manager`, exact positive counts, canonical JSON + SHA-256 | direct output and digest regressions |
| No universal target / no high-impact authority | fixed evidence state and decision-authority labels; no recommendation code path | public contract + ADR 0133 |
| Exact owned coverage | dedicated `Position Span of Control Quality` workflow runs the complete HRIS-kernel suite with existing exact 100% statement/branch thresholds | `.github/workflows/position-span-of-control-quality.yml` |

## Dependency and integration rule

PR #94 must integrate first. A focused GREEN result on #133 is stack-local only. After parent integration, retarget #133 to fresh `develop`, reconcile any parent changes, then rerun every applicable Workforce/People/Job-Analysis/Foundation/Recovery/SAST/Security and central required workflow on one new exact head. Parent checks, reviews and statuses never transfer.

## Scientific interpretation guard

Primary research shows span of control can matter but varies with work complexity, hierarchy and organizational goals. Orgmetra therefore exposes direct-report Position counts as inspectable structural evidence only. Any later evaluative or prescriptive use requires separate contextual evidence and accountable human review.
