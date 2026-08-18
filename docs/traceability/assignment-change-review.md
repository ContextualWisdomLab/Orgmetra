# Assignment-change review traceability

**Status:** active PR / proposed capability. Not protected-main truth until merged from one fully validated exact head.

| Requirement | Design / implementation evidence | Executable evidence |
|---|---|---|
| Keep Person/Employment/Assignment/Job/Position identities separate | `AssignmentChangeReviewPacket` has distinct expected-namespace opaque references for each concept | `test_packet_correlates_policy_and_evidence_without_copying_worker_values`, reference-validation matrix |
| Preserve PII, compensation, allocation-value, and narrative minimization | Envelope has no person-name/contact, compensation amount, allocation ratio, or free-form model-output field; immutable flags remain false; reason is a controlled category | `test_builds_value_free_pre_mutation_review_packet`, reason-code regressions, direct-construction governance matrix |
| Bind exact review evidence and policy version | Current-scope snapshot, allocation plan, allocation policy, worker-impact assessment, and communication plan each carry an opaque reference and SHA-256 digest | digest/reference validation matrices; canonical JSON/digest regression |
| Do not infer authoritative temporal scope from identifiers | `scope_verification_state` is fixed to `requires_authoritative_resolution` and next action requires live authoritative verification | direct-construction governance matrix |
| Keep high-impact assignment action under accountable human authority | requester and reviewer are separate; human confirmation is mandatory; decision authority is `human_review_only` | requester/reviewer separation regression; direct-construction governance matrix |
| Packet must not authorize persistence | `mutation_state=not_authorized_to_apply`; next action routes approved change to authoritative People mutation boundary | direct-construction governance matrix |
| Keep evidence deterministic without timestamp truncation | precision-preserving UTC RFC 3339 canonicalization and SHA-256 over canonical JSON | deterministic digest and sub-second timestamp regressions |
| Reject ambiguous governance identity | canonical non-sentinel tenant UUID and namespace-specific UUID reference grammar | tenant/reference validation matrices |
| Exact 100% owned statement and branch coverage | dedicated exact-head workflow uses hash-locked shared test toolchain and `--cov-fail-under=100` with branch coverage | `.github/workflows/assignment-change-review-quality.yml` |

The packet deliberately does not prove Position capacity, policy/legal permissibility, worker consultation, collective-agreement requirements, or mutation success. Those remain authoritative runtime/policy evidence and must not be inferred from the packet digest.
