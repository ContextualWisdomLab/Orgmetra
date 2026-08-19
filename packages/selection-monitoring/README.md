# Orgmetra Selection Monitoring

`orgmetra-selection-monitoring` defines a governed, aggregate-only evidence packet for planning post-selection outcome monitoring. It is intentionally not a statistics engine, legal decision engine, or candidate-level evidence store.

## What the contract binds

A `SelectionOutcomeMonitoringPlan` ties one tenant and authoritative Job to the total selection process being monitored, an aggregate population snapshot, an aggregate selection-outcome snapshot, the protected-attribute handling policy, small-sample interpretation policy, statistical analysis plan, accountable requester and reviewer references, an explicit monitoring window, and a bounded positive `evidence_version`.

Every trust-bearing artifact is represented by a bounded namespaced reference whose suffix is a canonical non-sentinel UUID, plus an independent SHA-256 digest where integrity evidence is required. Human-readable, value-bearing, sentinel, and noncanonical reference suffixes are rejected so Job labels, policy values, protected-attribute concepts, actor names, or other sensitive semantics cannot be smuggled through a field described as opaque. `reason_code` is closed to the reviewed non-sensitive `quarterly_selection_governance` value for this initial contract, rather than accepting arbitrary lower-snake-case text. `evidence_version` must be a true integer from 1 through 2147483647 and participates in canonical JSON and SHA-256 evidence, so revisions to the actor/purpose/reason-bound monitoring evidence cannot silently collide. Canonical JSON and a packet digest support immutable audit correlation without copying candidate identities, protected-attribute values, assessment scores, individual decisions, or free-form model output.

The ordinary representation is fully redacted as `SelectionOutcomeMonitoringPlan(<redacted>)`, so routine logs and assertion failures do not expose Job, actor, policy, snapshot, or statistical-plan correlations. Canonical JSON remains the explicit evidence serialization boundary. UUID-backed correlations are value-minimized metadata, not anonymous data, and remain subject to purpose-bound authorization, least privilege, retention/export controls, and audit.

## Governance boundary

The packet always remains `requires_human_review`, requires explicit human confirmation, and fixes decision authority to `human_review_only`. Its analysis scope is the total selection process for one Job. It does not calculate selection rates, apply the four-fifths rule, estimate statistical significance, infer discrimination, or make an employment-process change.

Different requester/reviewer references are only an early syntactic guard. Before review, the host must re-resolve `actor_reference` and `reviewer_reference` within the exact `tenant_record_id` through the authoritative actor boundary and prove their resolved actor identities are distinct. It must then verify Job scope, aggregate population completeness, protected-attribute handling, small-sample policy, and statistical-plan provenance before routing the evidence to an authorized analyst and accountable human reviewer for any process change or legal conclusion.

## Example

```python
from datetime import date, datetime, timezone

from orgmetra_selection_monitoring import build_selection_outcome_monitoring_plan

plan = build_selection_outcome_monitoring_plan(
    tenant_record_id="11111111-1111-4111-8111-111111111111",
    monitoring_plan_reference="selection_monitoring_plan:10000000-0000-4000-8000-000000000001",
    job_profile_reference="job_profile:10000000-0000-4000-8000-000000000002",
    selection_process_reference="selection_process:10000000-0000-4000-8000-000000000003",
    population_snapshot_reference="population_snapshot:10000000-0000-4000-8000-000000000004",
    population_snapshot_digest="a" * 64,
    outcome_snapshot_reference="selection_outcome_snapshot:10000000-0000-4000-8000-000000000005",
    outcome_snapshot_digest="b" * 64,
    protected_attribute_policy_reference="protected_attribute_policy:10000000-0000-4000-8000-000000000006",
    protected_attribute_policy_digest="c" * 64,
    small_sample_policy_reference="small_sample_policy:10000000-0000-4000-8000-000000000007",
    small_sample_policy_digest="d" * 64,
    statistical_plan_reference="statistical_plan:10000000-0000-4000-8000-000000000008",
    statistical_plan_digest="e" * 64,
    actor_reference="actor:10000000-0000-4000-8000-000000000009",
    reviewer_reference="actor:10000000-0000-4000-8000-00000000000a",
    monitoring_start=date(2026, 1, 1),
    monitoring_end=date(2026, 3, 31),
    purpose_code="selection_outcome_monitoring",
    reason_code="quarterly_selection_governance",
    generated_at=datetime(2026, 4, 2, 8, 30, tzinfo=timezone.utc),
    evidence_version=1,
)
```

This package writes no database tables and performs no cross-service SQL. A future persistence or analytics implementation must preserve purpose-bound authorization, authoritative actor resolution, aggregate-only/minimum-necessary access, small-sample controls, immutable audit evidence, and accountable human review independently.
