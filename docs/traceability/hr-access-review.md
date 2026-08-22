# HR Access Review Traceability

Status: **active PR only**. This document does not describe protected-main truth until the branch is integrated.

## Buyer requirement → executable evidence

| Requirement | Implementation | Regression / evidence |
| --- | --- | --- |
| Periodically or eventfully review existing HR access without exposing HR values | `HrAccessReviewPacket` stores opaque references plus scope/policy/entitlement digests only | `test_builds_value_minimized_non_enforcing_access_review_evidence` |
| Preserve least privilege without making review evidence an enforcement command | Closed recommendations are retain/reduce/remove existing access; fixed enforcement state is `not_authorized_to_modify_access` | `test_supports_reviewed_reduction_and_removal_without_execution_authority`, rejection of expansion vocabulary |
| Require accountable human separation | Reviewer must differ from requester and reviewed subject | `test_requires_independent_reviewer` |
| Re-resolve live identity and authorization state before enforcement | Fixed `scope_verification_state=requires_authoritative_resolution` and action-oriented next step | canonical-document assertions |
| Preserve audit correlation without HR PII or credentials | Tenant/review/actor references and SHA-256 evidence only; redacted repr | value-minimization regression |
| Fail closed on runtime-polymorphism attacks | Trust-bearing strings, integer versions, timestamps and fixed states require exact built-in primitives | hostile runtime and invalid primitive regressions |
| Detect in-process post-construction evidence rewrite | Verified canonical export compares current evidence with a process-local creation digest | `test_detects_post_construction_evidence_rewrite_and_unregistered_copy` |
| Maintain exact owned coverage | Dedicated exact-head workflow | `HR Access Review Quality` requires 100% statement + branch coverage and clean checkout |

## Ownership boundary

This lane writes only Orgmetra. It does not mutate Keyverse, central `.github`, or another dedicated-writer repository. `actor:` references are opaque correlation for later authoritative identity resolution; they are not credentials or proof that the named actor is currently authenticated.

The packet is not an access-grant/revoke API, does not write foreign application tables, and does not claim that a review recommendation has been enforced. A downstream access mutation must independently re-resolve actor, tenant, purpose, resource scope, policy, current entitlement state, and reviewer authority, then emit its own immutable audit/outbox evidence.

## Standards interpretation

NIST SP 800-53 Rev. 5 AC-2 requires account-management review at an organization-defined frequency, AC-5 supports separation of duties, and AC-6 states the least-privilege principle. They are design evidence rather than a certification claim. No universal review frequency is hard-coded here.
