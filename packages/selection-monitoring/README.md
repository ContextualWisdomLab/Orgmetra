# Orgmetra Selection Monitoring

`orgmetra-selection-monitoring` defines a governed, aggregate-only evidence packet for planning post-selection outcome monitoring. It is intentionally not a statistics engine, legal decision engine, or candidate-level evidence store.

## What the contract binds

A `SelectionOutcomeMonitoringPlan` ties one tenant and authoritative Job to the total selection process being monitored, an aggregate population snapshot, an aggregate selection-outcome snapshot, the protected-attribute handling policy, small-sample interpretation policy, statistical analysis plan, accountable requester and reviewer references, an explicit monitoring window, a system-recorded generation instant, and a bounded positive `evidence_version`.

`tenant_record_id` follows Orgmetra's authoritative canonical non-sentinel operational UUID contract instead of imposing a second UUID-version policy at this leaf package. Packet-owned trust-bearing artifacts remain canonical non-sentinel UUIDv4 identities; namespaced artifact references additionally require their expected namespace. UUIDv1 and other non-v4 suffixes are rejected for those references so timestamp/node-derived or otherwise nonconforming identifiers cannot masquerade as the package's opaque trust-reference format. Human-readable, value-bearing, sentinel, and noncanonical reference suffixes are also rejected so Job labels, policy values, protected-attribute concepts, actor names, or other sensitive semantics cannot be smuggled through a field described as opaque. Content-bearing evidence adds an independent SHA-256 digest where integrity evidence is required. `reason_code` is closed to the reviewed non-sensitive `quarterly_selection_governance` value for this initial contract, rather than accepting arbitrary lower-snake-case text. `evidence_version` must be a true integer from 1 through 2147483647 and participates in canonical JSON and SHA-256 evidence, so revisions to the actor/purpose/reason-bound monitoring evidence cannot silently collide. Canonical JSON and a packet digest support immutable audit correlation without copying candidate identities, protected-attribute values, assessment scores, individual decisions, or free-form model output.

`generated_at` is issuance-time evidence rather than a caller-controlled timezone object retained for later execution. Construction requires an exact built-in `datetime`, resolves any concrete `tzinfo` offset once, converts the result to a built-in UTC `datetime`, rejects future instants, and stores only that detached UTC instant. Later canonical export never invokes the caller's original timezone provider, so a mutable or stateful `tzinfo` cannot rewrite already-issued evidence. Provider exceptions, missing concrete offsets, and UTC-normalization overflow fail closed as `ValueError`; low-level reinjection of a non-UTC timestamp also fails before evidence emission.

A frozen dataclass is not by itself issuance evidence because low-level Python mutation can still rewrite otherwise valid values. Each live issued plan is therefore bound to its exact construction-time canonical JSON by a process-local HMAC seal stored outside packet-writable slots. Seal registration is single-use per live object identity: explicitly re-running `__post_init__()` cannot replace an existing seal after a low-level valid-value rewrite. `canonical_json()` snapshots the current canonical bytes once, verifies that exact snapshot against the external issuance seal, and returns the verified snapshot rather than rereading the object. A valid-value rewrite, attempted seal renewal, or missing process-local issuance evidence fails closed. This mechanism is defense-in-depth for in-process misuse only; durable cross-process uniqueness, purpose authorization, and immutable audit/outbox remain responsibilities of the authoritative host or persistence boundary.

The ordinary representation is fully redacted as `SelectionOutcomeMonitoringPlan(<redacted>)`, so routine logs and assertion failures do not expose tenant, Job, actor, policy, snapshot, or statistical-plan correlations. Canonical JSON remains the explicit evidence serialization boundary. UUID-backed correlations are value-minimized metadata, not anonymous data, and remain subject to purpose-bound authorization, least privilege, retention/export controls, and audit.

## Governance boundary

The packet always remains `requires_human_review`, requires explicit human confirmation, and fixes decision authority to `human_review_only`. Its analysis scope is the total selection process for one Job. It does not calculate selection rates, apply the four-fifths rule, estimate statistical significance, infer discrimination, or make an employment-process change.

Different requester/reviewer references are only an early syntactic guard. Before review, the host must re-resolve **every packet reference** within the exact `tenant_record_id` through its authoritative boundary so a syntactically valid reference from another tenant cannot be mixed into the monitoring envelope. It must specifically re-resolve `actor_reference` and `reviewer_reference` and prove their resolved actor identities are distinct, then verify Job scope, aggregate population completeness, protected-attribute handling, small-sample policy, and statistical-plan provenance before routing the evidence to an authorized analyst and accountable human reviewer for any process change or legal conclusion. UUIDv4 constrains packet-owned trust-reference opacity only; it does not establish tenant ownership, actor identity, or evidence validity. Tenant UUID generation/privacy policy remains owned by the authoritative HRIS boundary.

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

This package writes no database tables and performs no cross-service SQL. A future persistence or analytics implementation must preserve purpose-bound authorization, authoritative tenant-scoped reference and actor resolution, aggregate-only/minimum-necessary access, small-sample controls, immutable audit evidence, and accountable human review independently.
