# Workforce composition traceability

## Status

Active-PR only. This evidence does not describe protected-`develop` product truth until PR #33 integrates.

| Requirement | Decision / contract | Production implementation | Executable evidence |
|---|---|---|---|
| Reconstruct workforce state at business and knowledge time | ADR 0011; explicit `(tenant_record_id, effective_on, known_at)` coordinate | `build_workforce_composition_snapshot` reuses bitemporal Employment and Assignment intervals | historical before/after correction, future-effective/late-recorded exclusion, and timezone-aware cutoff regressions |
| Avoid double-counting valid concurrent workers | ADR 0011 | distinct `person_record_id` set across visible reportable employments | concurrent-employment fixture expects 2 people from 3 reportable employments |
| Reject impossible employment portfolios before aggregation | Existing employment-concurrency invariant + ADR 0011 | `_validate_visible_employment_portfolios` reuses `validate_person_employment_exclusivity` at the report coordinate | overlapping-exclusive-employment regression expects fail-closed `EmploymentExclusivityError` |
| Preserve employment/FTE portfolio shape | ADR 0011 | employment count, staffed assignment count and Decimal staffed FTE remain separate aggregates | concurrent portfolio fixture expects 3 employments, 3 assignments and 1.5000 FTE |
| Reject overfilled Position seats before aggregation | Existing position-seat invariant + ADR 0011 | each visible `position_record_id` is revalidated with `validate_position_seat_capacity` at the report coordinate | two distinct workers allocating 0.6000 each to one Position must raise `PositionSeatError` instead of reporting 1.2000 staffed FTE |
| Fail closed on inconsistent authoritative truth | Existing HRIS integrity contracts + ADR 0011 | single-valued Employment resolution, duplicate Assignment detection, assignment-employment coverage and allocation validation | contradictory Employment, duplicate Assignment, person mismatch and >1.0000 per-employment allocation regressions |
| Prevent cross-tenant metric contamination | ADR 0003 + ADR 0011 | tenant scope is applied before reconstruction or aggregation | foreign-tenant employment/assignment fixture does not affect tenant metrics |
| Minimize downstream PII | ADR 0011 | canonical JSON includes aggregate metrics, opaque tenant ID and report coordinates only | canonical evidence regression rejects row-level `person_record` / `employment_record` names |
| Make aggregate evidence reproducible | ADR 0011 | sorted status tuples, deterministic JSON encoding and SHA-256 over exact UTF-8 bytes | reversed-input fixture requires identical canonical JSON and digest; empty-workforce fixture requires stable empty status evidence |
| Keep workforce intelligence descriptive | ADR 0011 | module contains no recommendation, decision, protected-attribute inference or persistence API | public package boundary and code review; high-impact actions remain outside this slice |
| Ground scope in current authoritative standards without claiming certification | ISO 30414:2025 public catalogue metadata; ADR 0011 | no proprietary ISO metric text is embedded in production code | `docs/doctoring/workforce-composition-references.md` |
| Keep exact owned coverage reproducible | Orgmetra quality policy | `.github/workflows/foundation-ci.yml` checks exact candidate SHA and runs the complete HRIS kernel | hosted exact-head workflow with package 100% statement/branch threshold |
