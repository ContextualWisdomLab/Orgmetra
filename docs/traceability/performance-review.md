# Performance review traceability

Status: **active PR / proposed capability**, not protected-main truth.

| Requirement | Evidence | Status |
|---|---|---|
| Bind review to authoritative Employment and Job scope | `PerformanceReviewPacket.employment_record_reference`, `job_profile_reference` | Implemented on active PR |
| Bind exact performance-cycle and business review period | `performance_cycle_reference`, `review_period_start`, `review_period_end` | Implemented on active PR |
| Bind predetermined criteria and goals | `criterion_set_reference`/digest, `goal_plan_reference`/digest | Implemented on active PR |
| Bind exact outcome evidence without copying values | `criterion_observation_snapshot_reference`/digest | Implemented on active PR |
| Preserve optional development provenance | paired `development_plan_reference`/digest | Implemented on active PR |
| Keep person PII, rating values, free-form feedback/model output outside packet | immutable false flags plus absence of value-bearing fields | Implemented on active PR |
| Require accountable human review | fixed `human_confirmation_required=True`, `decision_authority=human_review_only`, `review_state=requires_human_review` | Implemented on active PR |
| Preserve deterministic immutable correlation evidence | canonical JSON plus SHA-256 | Implemented on active PR |
| Exact 100% owned statement/branch coverage | `packages/performance-review/pyproject.toml`, `.github/workflows/performance-review-quality.yml` | Required on exact PR head |
| Standards/research basis | ADR 0018; `docs/doctoring/performance-review-references.md` | Documented on active PR |

The packet does not persist or calculate a rating, decide compensation, infer performance, or prove scientific validity/fairness/compliance. Those claims require their own authoritative evidence and controls.
