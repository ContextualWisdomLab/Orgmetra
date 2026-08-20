# Assignment-change review traceability

**Status:** active PR / proposed capability. Not protected-main truth until merged from one fully validated exact head.

| Requirement | Design / implementation evidence | Executable evidence |
|---|---|---|
| Keep Person/Employment/Assignment/Job/Position identities separate | `AssignmentChangeReviewPacket` has distinct expected-namespace opaque references for each concept | `test_packet_correlates_policy_and_evidence_without_copying_worker_values`, reference-validation matrix |
| Keep trust references opaque and non-correlating by UUID version | namespaced packet references require canonical non-sentinel UUIDv4 suffixes | `test_rejects_uuid1_trust_references_through_builder_and_replace` rejects UUIDv1 timestamp/node correlation across every trust-reference field and both construction paths |
| Preserve PII, compensation, allocation-value, and narrative minimization | Envelope has no person-name/contact, compensation amount, allocation ratio, or free-form model-output field; immutable flags remain false; reason is a controlled category | `test_builds_value_free_pre_mutation_review_packet`, reason-code regressions, direct-construction governance matrix |
| Bind exact review evidence and policy version | Current-scope snapshot, allocation plan, allocation policy, worker-impact assessment, and communication plan each carry an opaque reference and SHA-256 digest | digest/reference validation matrices; canonical JSON/digest regression |
| Version high-impact actor/purpose/reason evidence | bounded positive `evidence_version` is included in canonical JSON/SHA-256 | `test_packet_carries_explicit_evidence_version`, version range and digest-change regressions |
| Do not infer authoritative temporal or tenant/worker scope from identifiers | `scope_verification_state` is fixed to `requires_authoritative_resolution`; next action requires every packet reference to be re-resolved within `tenant_record_id`, then verifies the Person-to-Employment-to-current-Assignment binding and current Assignment/Job/Position worker scope before proposed-scope approval | `test_next_action_requires_tenant_scoped_worker_binding_resolution`; direct-construction governance matrix |
| Prove requester/reviewer separation at the authoritative actor boundary | identical references are rejected locally; next action requires tenant-scoped resolution of `requester_reference` and `reviewer_reference` and proof that resolved identities are distinct | `test_requester_and_reviewer_require_authoritative_actor_separation` plus existing requester/reviewer separation regression |
| Keep high-impact assignment action under accountable human authority | human confirmation is mandatory; decision authority is `human_review_only` | direct-construction governance matrix |
| Packet must not authorize persistence | `mutation_state=not_authorized_to_apply`; next action routes approved change to authoritative People mutation boundary | direct-construction governance matrix |
| Keep evidence deterministic without timestamp truncation | precision-preserving UTC RFC 3339 canonicalization and SHA-256 over canonical JSON | deterministic digest and sub-second timestamp regressions |
| Reject ambiguous governance identity | canonical non-sentinel tenant UUID and namespace-specific UUIDv4 reference grammar | tenant/reference validation matrices plus UUIDv1 regression |
| Exact 100% owned statement and branch coverage | dedicated exact-head workflow uses hash-locked shared test toolchain and `--cov-fail-under=100` with branch coverage | `.github/workflows/assignment-change-review-quality.yml` |

The packet deliberately does not prove actor identity, Position capacity, policy/legal permissibility, worker consultation, collective-agreement requirements, or mutation success. Those remain authoritative runtime/policy evidence and must not be inferred from the packet digest or reference-string inequality.
