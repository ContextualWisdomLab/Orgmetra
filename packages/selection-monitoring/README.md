# Orgmetra Selection Monitoring

`orgmetra-selection-monitoring` defines a governed, aggregate-only evidence packet for planning post-selection outcome monitoring. It is intentionally not a statistics engine, legal decision engine, or candidate-level evidence store.

## What the contract binds

A `SelectionOutcomeMonitoringPlan` ties one tenant and authoritative Job to the total selection process being monitored, an aggregate population snapshot, an aggregate selection-outcome snapshot, the protected-attribute handling policy, small-sample interpretation policy, statistical analysis plan, accountable requester and distinct reviewer, and an explicit monitoring window.

Every trust-bearing artifact is represented by a bounded opaque reference plus an independent SHA-256 digest. Canonical JSON and a packet digest support immutable audit correlation without copying candidate identities, protected-attribute values, assessment scores, individual decisions, or free-form model output.

## Governance boundary

The packet always remains `requires_human_review`, requires explicit human confirmation, and fixes decision authority to `human_review_only`. Its analysis scope is the total selection process for one Job. It does not calculate selection rates, apply the four-fifths rule, estimate statistical significance, infer discrimination, or make an employment-process change.

The next action is deliberately operational: verify Job scope, aggregate population completeness, protected-attribute handling, small-sample policy, and statistical-plan provenance; then route the evidence to an authorized analyst and accountable human reviewer before any process change or legal conclusion.

## Example

```python
from datetime import date, datetime, timezone

from orgmetra_selection_monitoring import build_selection_outcome_monitoring_plan

plan = build_selection_outcome_monitoring_plan(
    tenant_record_id="11111111-1111-4111-8111-111111111111",
    monitoring_plan_reference="selection_monitoring_plan:plan-001",
    job_profile_reference="job_profile:job-001",
    selection_process_reference="selection_process:process-001",
    population_snapshot_reference="population_snapshot:population-001",
    population_snapshot_digest="a" * 64,
    outcome_snapshot_reference="selection_outcome_snapshot:outcomes-001",
    outcome_snapshot_digest="b" * 64,
    protected_attribute_policy_reference="protected_attribute_policy:policy-001",
    protected_attribute_policy_digest="c" * 64,
    small_sample_policy_reference="small_sample_policy:policy-001",
    small_sample_policy_digest="d" * 64,
    statistical_plan_reference="statistical_plan:plan-001",
    statistical_plan_digest="e" * 64,
    actor_reference="actor:requester-001",
    reviewer_reference="actor:reviewer-001",
    monitoring_start=date(2026, 1, 1),
    monitoring_end=date(2026, 3, 31),
    purpose_code="selection_outcome_monitoring",
    reason_code="quarterly_selection_governance",
    generated_at=datetime(2026, 4, 2, 8, 30, tzinfo=timezone.utc),
)
```

This package writes no database tables and performs no cross-service SQL. A future persistence or analytics implementation must preserve purpose-bound authorization, aggregate-only/minimum-necessary access, small-sample controls, immutable audit evidence, and accountable human review independently.
