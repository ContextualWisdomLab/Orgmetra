# Performance Goal Plan Traceability

Status: **active PR; not protected-main truth until merged**.

| Requirement | Implementation | Executable evidence |
| --- | --- | --- |
| Bind goal plans to authoritative HR scope | `PerformanceGoalPlanPacket` tenant/Employment/Job/cycle references | `test_builds_value_minimized_goal_plan_evidence`, `test_accepts_operational_non_v4_core_references` |
| Preserve goal and measurement provenance without durable goal text | SHA-256 goal-set and measurement-definition digests | `test_rejects_invalid_identity_and_provenance_values` |
| Require accountable human review | distinct requester/reviewer plus fixed human-review state | `test_requires_distinct_requester_and_reviewer`, `test_rejects_governance_drift` |
| Never turn plan evidence into a rating or employment decision | fixed non-authority states | `test_rejects_governance_drift` |
| Bind reviewed feedback cadence | closed cadence vocabulary | `test_rejects_unreviewed_feedback_cadence` |
| Preserve canonical audit integrity | exact runtime primitives, live reference binding, creation digest | runtime-integrity regressions in `tests/test_plan.py` |

The package is a transport-neutral governance boundary. Authoritative persistence, purpose-bound HR content access, immutable audit/outbox recording, and later performance-review decisions remain separate Orgmetra responsibilities.
