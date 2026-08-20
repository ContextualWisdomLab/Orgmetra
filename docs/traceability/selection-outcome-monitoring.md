# Selection-outcome monitoring traceability

## Status

**Active PR / proposed capability.** This file does not describe protected-`develop` behavior until the owning PR is integrated.

## Buyer need → contract evidence

| Buyer / governance need | Owned contract evidence | Explicit non-claim |
|---|---|---|
| Monitor the correct hiring/promotion process | Canonical UUIDv4 `tenant_record_id`, exact UUIDv4-backed `job_profile_reference` and `selection_process_reference`; fixed `analysis_scope=total_selection_process_by_job`; immutable next action requires every packet reference to be re-resolved within exact `tenant_record_id` | UUID syntax alone is not tenant authority or component-level causality evidence |
| Reproduce the monitored population and outcomes | Exact UUIDv4-backed aggregate population/outcome snapshot references plus independent SHA-256 digests | No candidate-level record or protected-attribute value in the packet |
| Preserve privacy and interpretation rules | Exact UUIDv4-backed protected-attribute handling and small-sample policy references/digests | No blanket authorization to expose protected-attribute data |
| Prevent semantic/value/correlation smuggling through public IDs | `tenant_record_id` and every governed reference require canonical non-sentinel UUIDv4 identity; namespaced references also require the expected prefix; `test_reference_privacy.py` covers UUIDv1 tenant identity plus value-bearing, sentinel, noncanonical and UUIDv1 reference cases through builder and `dataclasses.replace(...)` paths | UUIDv4 syntax does not prove source truth, tenant membership, or authorization |
| Prevent cross-tenant evidence mixing | `test_actor_separation.py` requires the governed next action to re-resolve every packet reference within `tenant_record_id` before actor separation, Job scope verification, or accountable review | The packet does not itself query authoritative stores |
| Bind the analysis method before interpretation | Exact UUIDv4-backed statistical-plan reference/digest | No statistics are calculated by this package |
| Version actor/purpose/reason evidence explicitly | `evidence_version` is a true positive integer through signed-int32 max and participates in canonical JSON/SHA-256 | `test_evidence_version.py` proves presence, digest separation, bounds, and `dataclasses.replace(...)` revalidation |
| Prove accountable requester/reviewer separation | Different opaque actor references as a syntactic guard plus tenant-scoped authoritative resolution requiring distinct resolved actor identities | Reference inequality alone is not identity or separation-of-duties evidence |
| Prevent automated high-impact action | Exact boolean human confirmation, `human_review_only`, `requires_human_review`, governed next action | No automated employment-process change or legal conclusion |
| Preserve replayable audit correlation | Precision-preserving UTC generation time, canonical JSON, SHA-256 packet digest | Digest proves envelope integrity, not source truth or scientific/legal validity |

## Executable evidence

`packages/selection-monitoring/tests/test_plan.py` exercises direct-constructor and builder validation, operational tenant identity, UUID-backed reference namespaces, SHA-256 digests, requester/reviewer syntactic separation, monitoring-window boundaries, governance codes, timezone handling, fractional-second evidence identity, immutable review/authority state, aggregate-only enforcement, canonical JSON, and deterministic packet hashing. `packages/selection-monitoring/tests/test_actor_separation.py` requires the immutable next action to re-resolve every packet reference in the exact tenant before Job-scope/accountable-review use, and separately requires requester/reviewer resolution through the authoritative tenant-scoped actor boundary with distinct resolved identities. `packages/selection-monitoring/tests/test_reference_privacy.py` is the RED→GREEN privacy contract for rejecting UUIDv1 public tenant identity plus human-readable/value-bearing, sentinel, noncanonical, and non-v4 opaque-reference suffixes through both public construction and replacement paths. `packages/selection-monitoring/tests/test_evidence_version.py` requires explicit bounded evidence revision identity in canonical evidence and proves that version changes alter the packet hash.

`.github/workflows/selection-monitoring-quality.yml` is supplemental exact-head evidence with hash-locked test tooling, 100% owned statement/branch coverage, exact-candidate checkout, and clean-checkout proof. It does not replace any organization-required central workflow.

## Ownership boundary

This slice writes only Orgmetra and introduces no database migration or cross-service SQL. Future statistical computation must use the appropriate published psychometric/statistical service contract rather than duplicating foreign kernels, and future access to protected-attribute data must remain purpose-bound and minimum-necessary. Authoritative tenant-scoped reference and actor resolution remains at the host boundary; this packet fails closed by requiring that proof before human review use.