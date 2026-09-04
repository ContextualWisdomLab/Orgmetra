# HR Access Review Traceability

Status: **active PR only**. This document does not describe protected-main truth until the branch is integrated.

## Buyer requirement → executable evidence

| Requirement | Implementation | Regression / evidence |
| --- | --- | --- |
| Periodically or eventfully review existing HR access without exposing HR values | `HrAccessReviewPacket` stores packet-local pseudonymous actor correlations, opaque review/tenant references, SHA-256 scope/policy/entitlement/reviewer-identity evidence, and bounded governance metadata rather than HR payload values | `test_builds_value_minimized_non_enforcing_access_review_evidence`, actor-reference privacy regressions |
| Bind the governance purpose explicitly | Canonical evidence fixes `purpose_code=hr_access_recertification` rather than inferring purpose from packet type | `test_binds_explicit_access_review_purpose`, direct governance-state drift regression |
| Preserve least privilege without making review evidence an enforcement command | Closed recommendations are retain/reduce/remove existing access; fixed enforcement state is `not_authorized_to_modify_access` | `test_supports_reviewed_reduction_and_removal_without_execution_authority`, rejection of expansion vocabulary |
| Require accountable human separation and identity provenance | Reviewer must differ from requester and reviewed subject, packet-local actor correlations are UUIDv4, and reviewer identity-resolution evidence is SHA-256 bound | `test_requires_independent_reviewer`, `test_binds_reviewer_identity_evidence_and_system_recorded_time`, actor-reference privacy regressions |
| Preserve human-review time separately from system-recorded time | Both are exact UTC primitives and `recorded_at` may not precede `reviewed_at` | `test_binds_reviewer_identity_evidence_and_system_recorded_time`, `test_requires_exact_utc_review_and_recorded_times` |
| Re-resolve live identity and authorization state before enforcement | Fixed `scope_verification_state=requires_authoritative_resolution` and action-oriented next step | canonical-document assertions |
| Preserve audit correlation without HR PII or credentials | Tenant/review references, packet-local pseudonymous actor correlations, SHA-256 evidence, fixed purpose, bounded review reason/recommendation, timestamps, evidence version, and fixed governance state are retained; redacted repr prevents routine log disclosure | value-minimization and actor-reference privacy regressions |
| Fail closed on runtime-polymorphism attacks | Trust-bearing strings, integer versions, timestamps and fixed states require exact built-in primitives | hostile runtime and invalid primitive regressions |
| Detect in-process post-construction evidence rewrite | Verified canonical export compares current evidence with a process-local creation digest | `test_detects_post_construction_evidence_rewrite_and_unregistered_copy` |
| Validate the distributable package rather than source-tree import behavior alone | Dedicated workflow builds the checked-out package, installs the generated wheel into an isolated test environment, and runs the same exact-coverage suite without source-tree `PYTHONPATH` | `HR Access Review Quality` artifact-install and clean-checkout steps |
| Maintain exact owned coverage | Dedicated exact-head workflow | `HR Access Review Quality` requires 100% statement + branch coverage and clean checkout |

## Ownership boundary

This lane writes only Orgmetra. It does not mutate Keyverse, central `.github`, or another dedicated-writer repository. The packet's `actor:` UUIDv4 values are Orgmetra-local pseudonymous audit correlations, not Keyverse subject-format requirements, credentials, or proof that an actor is currently authenticated. The host must obtain or derive them only after authoritative identity resolution and preserve that provenance separately; the reviewer identity digest binds upstream identity-resolution evidence without copying identity payloads into this packet.

The packet is not an access-grant/revoke API, does not write foreign application tables, and does not claim that a review recommendation has been enforced. A downstream access mutation must independently re-resolve actor, tenant, purpose, resource scope, policy, current entitlement state, reviewer identity evidence and reviewer authority, then emit its own immutable audit/outbox evidence.

`reviewed_at` is the human review event time. `recorded_at` is the later-or-equal system-recorded evidence time supplied at this application boundary. Durable database transaction time is not claimed until canonical evidence enters Orgmetra's immutable audit/outbox persistence boundary.

## Standards interpretation

NIST SP 800-53 Rev. 5 AC-2 requires account-management review at an organization-defined frequency, AC-5 supports separation of duties, and AC-6 states the least-privilege principle. They are design evidence rather than a certification claim. No universal review frequency is hard-coded here.
