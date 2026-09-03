# Position vacancy traceability

## Truth state

- Protected-main truth: Position and Assignment are separate tenant-scoped bitemporal HRIS facts; existing Position coverage and seat-capacity integrity are authoritative.
- Active PR #97 only: `PositionVacancySnapshot` and `build_position_vacancy_snapshot(...)` derive PII-minimized vacancy/fill evidence.
- Planned/out of scope here: requisition creation, headcount-budget authorization, forecasts, dashboards and automated workforce action.

## Requirement-to-evidence map

| Requirement | Production boundary | Regression evidence |
|---|---|---|
| Preserve effective and system-recorded time | `build_position_vacancy_snapshot` | `test_future_position_and_assignment_are_not_visible`, `test_naive_knowledge_cutoff_fails_before_resolution`, `test_snapshot_rejects_unrepresentable_utc_time` |
| Preserve tenant isolation | Position/Assignment filtering at the explicit tenant coordinate | `test_snapshot_reports_vacant_partial_full_and_excludes_other_tenant_and_closed` |
| Reuse Position staffing integrity | `validate_assignment_position_coverage`, `validate_position_seat_capacity` | `test_assignment_to_nonstaffable_position_fails_closed`, `test_overfilled_position_fails_closed` |
| Reject contradictory Assignment identity | visible Assignment identity guard | `test_duplicate_visible_assignment_identity_fails_closed` |
| Do not hide unknown Position states | known-status fail-closed boundary | `test_unknown_visible_position_status_fails_closed` |
| Preserve fractional multiple membership | allocation aggregation by Position | `test_split_assignments_that_sum_to_one_are_fully_staffed` |
| Preserve canonical four-decimal FTE evidence, including zero | four-decimal `_ZERO` accumulator used by `build_position_vacancy_snapshot` | `test_future_position_and_assignment_are_not_visible` asserts `"staffed_fte":"0.0000"` |
| Minimize downstream PII | `PositionVacancySnapshot.canonical_json` | `test_snapshot_reports_vacant_partial_full_and_excludes_other_tenant_and_closed` |
| Reject forged aggregate evidence shape | `PositionVacancySnapshot.__post_init__` | direct-construction count/FTE/reconciliation/time regressions |
| Deterministic audit correlation | `content_digest` over canonical UTF-8 JSON | canonical/digest assertion in buyer snapshot regression |

## Merge evidence required

The owning exact head must have terminal GREEN Workforce Intelligence, Foundation CI, Recovery, SAST and Security evidence, with no still-valid unresolved review finding. Predecessor, cancelled, skipped, queued, pending or status-only evidence is non-passing. Integration additionally remains blocked by the repository-level independent-review and enforceable protected-branch requirements tracked in issue #89.
