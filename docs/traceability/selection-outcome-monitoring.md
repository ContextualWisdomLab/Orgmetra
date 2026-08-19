# Selection-outcome monitoring traceability

## Status

**Active PR / proposed capability.** This file does not describe protected-`develop` behavior until the owning PR is integrated.

## Buyer need → contract evidence

| Buyer / governance need | Owned contract evidence | Explicit non-claim |
|---|---|---|
| Monitor the correct hiring/promotion process | Exact UUID-backed `job_profile_reference` and `selection_process_reference`; fixed `analysis_scope=total_selection_process_by_job` | No component-level causality claim |
| Reproduce the monitored population and outcomes | Exact UUID-backed aggregate population/outcome snapshot references plus independent SHA-256 digests | No candidate-level record or protected-attribute value in the packet |
| Preserve privacy and interpretation rules | Exact UUID-backed protected-attribute handling and small-sample policy references/digests | No blanket authorization to expose protected-attribute data |
| Prevent semantic/value smuggling through opaque IDs | Canonical non-sentinel UUID suffix required for every namespaced reference; `test_reference_privacy.py` covers value-bearing, sentinel, noncanonical, builder, and `dataclasses.replace(...)` paths | UUID syntax does not prove source truth or authorization |
| Bind the analysis method before interpretation | Exact UUID-backed statistical-plan reference/digest | No statistics are calculated by this package |
| Prove accountable requester/reviewer separation | Different opaque actor references as a syntactic guard plus tenant-scoped authoritative resolution requiring distinct resolved actor identities | Reference inequality alone is not identity or separation-of-duties evidence |
| Prevent automated high-impact action | Exact boolean human confirmation, `human_review_only`, `requires_human_review`, governed next action | No automated employment-process change or legal conclusion |
| Preserve replayable audit correlation | Precision-preserving UTC generation time, canonical JSON, SHA-256 packet digest | Digest proves envelope integrity, not source truth or scientific/legal validity |

## Executable evidence

`packages/selection-monitoring/tests/test_plan.py` exercises direct-constructor and builder validation, operational tenant identity, UUID-backed reference namespaces, SHA-256 digests, requester/reviewer syntactic separation, monitoring-window boundaries, governance codes, timezone handling, fractional-second evidence identity, immutable review/authority state, aggregate-only enforcement, canonical JSON, and deterministic packet hashing. `packages/selection-monitoring/tests/test_actor_separation.py` requires the immutable next action to resolve requester/reviewer through the authoritative tenant-scoped actor boundary and prove distinct resolved identities. `packages/selection-monitoring/tests/test_reference_privacy.py` is the RED→GREEN privacy contract for rejecting human-readable/value-bearing, sentinel, and noncanonical opaque-reference suffixes through both public construction and replacement paths.

`.github/workflows/selection-monitoring-quality.yml` is supplemental exact-head evidence with hash-locked test tooling, 100% owned statement/branch coverage, exact-candidate checkout, and clean-checkout proof. It does not replace any organization-required central workflow.

## Ownership boundary

This slice writes only Orgmetra and introduces no database migration or cross-service SQL. Future statistical computation must use the appropriate published psychometric/statistical service contract rather than duplicating foreign kernels, and future access to protected-attribute data must remain purpose-bound and minimum-necessary. Authoritative actor resolution remains at the host identity boundary; this packet only fails closed by requiring that proof before human review use.
