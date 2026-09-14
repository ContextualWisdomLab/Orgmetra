# Requisition review packet traceability

## Maturity

**Active PR only.** Protected `develop` does not contain this capability until the candidate branch is integrated with fresh protected-head evidence.

## Requirement-to-evidence map

| Requirement | Owned object | Executable evidence |
|---|---|---|
| Bind one planned opening to an authoritative Job without copying candidate/employee PII values | `RequisitionReviewPacket.job_profile_reference` and opaque requisition reference | canonical payload regression proves no candidate/person/email/name fields are emitted |
| Keep trust-bearing correlations opaque | every namespaced reference | direct-builder and `dataclasses.replace(...)` regressions reject human-readable/value-bearing, sentinel, noncanonical, and wrong-namespace reference suffixes; accepted suffixes are canonical operational UUIDs |
| Minimize governance metadata | `reason_code`, `requirements_version_code` | reason is closed to reviewed non-sensitive `approved_growth_plan`; requirements version is restricted to `requirements_version_<positive-integer>`; semantic/personal/value-bearing variants fail closed |
| Prevent routine log disclosure | `RequisitionReviewPacket.__repr__` | representation regression requires exactly `RequisitionReviewPacket(<redacted>)` and proves representative references/digest are absent |
| Preserve Job/Position separation | required `job_profile_reference`, optional `position_record_reference` | one exact Position accepts one opening; multi-opening + exact Position is rejected |
| Bind current job requirements without owning Job Analysis tables | `job_requirements_reference`, `job_requirements_digest`, `requirements_version_code` | UUID-backed reference, numeric version-code, and lowercase SHA-256 regressions |
| Require authorized headcount evidence | `headcount_authorization_reference` | UUID-backed opaque reference validation; no finance/payroll values copied |
| Preserve accountable human actors and separation of duties | `hiring_manager_actor_reference`, `approver_actor_reference`; identical references rejected locally; governed next action requires tenant-scoped authoritative resolution and distinct resolved actor identities | `test_hiring_manager_and_approver_require_authoritative_separation` plus actor UUID/direct-constructor contract |
| Keep requisition approval human | `human_confirmation_required=True`, `review_state="requires_human_approval"`, governed `next_action` | direct-constructor regressions reject false/non-boolean confirmation, alternate state, and automatic-opening copy |
| Bound opening cardinality | `requested_opening_count` | bool/non-integer/zero/>100 rejection and exact-position one-seat invariant |
| Produce stable immutable correlation evidence | canonical JSON plus SHA-256 | deterministic serialization and independent SHA-256 recomputation regression |
| Avoid host-time ambiguity | timezone-aware `generated_at`, canonical UTC rendering | naive/unknown-offset rejection, non-UTC-to-UTC canonicalization, and fractional-second preservation regressions |
| Meet owned production coverage gate | `orgmetra_requisition_review` | Foundation CI requires exact 100% statement and branch coverage |

## Authority boundary

The packet does not persist an authoritative requisition, create a Position, create or modify a Job, allocate budget, resolve actor identity, create a candidate, access assessment values, make a selection decision, or create employment. Opaque references remain sensitive correlating metadata rather than anonymous values. Before approval, the host must resolve hiring-manager and approver references within the packet tenant and prove the authoritative identities are distinct. Downstream operations remain in their authoritative service boundaries and must independently enforce purpose-bound authorization, idempotency, human confirmation where applicable, and immutable audit/outbox evidence.

No foreign dedicated-writer repository is mutated or queried through application-table SQL by this slice.
