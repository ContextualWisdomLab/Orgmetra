# Compensation change review traceability

Status: **active PR only / proposed**, not protected-`develop` product truth until merged.

| Buyer or governance need | Contract | Executable evidence |
| --- | --- | --- |
| Correlate a proposed pay change without copying pay amounts | Opaque Person/Employment/current/proposed compensation references + independent digests; compensation/protected values excluded | `test_builds_deterministic_value_minimized_packet`, `test_every_reference_and_digest_is_validated` |
| Prevent tenant/reference identity from becoming a correlation smuggling channel | `tenant_record_id` and every namespaced trust-bearing reference require canonical non-sentinel UUIDv4 identity; UUIDv1 and other UUID versions fail closed | `test_rejects_uuid1_tenant_identity`, `test_invalid_core_inputs_fail_closed`, `test_every_reference_and_digest_is_validated`, `test_uuid1_trust_reference_is_rejected_by_builder_and_replace` |
| Preserve accountable separation of duties | Requester/reviewer references differ; canonical next action requires tenant-scoped identity re-resolution and distinct resolved actors | `test_same_opaque_actor_reference_is_rejected_early`, `test_next_action_requires_identity_scope_and_evidence_before_approval` |
| Prevent review evidence from authorizing a high-impact action | Human-only review, unresolved authoritative scope, no HRIS mutation, no external execution are immutable | `test_direct_constructor_and_replace_fail_closed` |
| Bind policy, equity, budget, payroll handoff, and evidence version | Independent SHA-256 digests and bounded positive `evidence_version` are canonical | `test_canonical_evidence_changes_with_governed_artifact_or_version`, `test_invalid_core_inputs_fail_closed` |
| Avoid accidental logging of worker/pay correlations | Generated dataclass representation disabled; custom representation fully redacted | `test_repr_redacts_personal_and_compensation_correlations` |
| Preserve exact audit time semantics | Timezone-aware timestamps normalize to UTC without discarding fractional precision | `test_fractional_and_offset_timestamps_preserve_distinct_instants`, `test_timezone_with_unknown_offset_is_rejected` |

## Quality gate

`.github/workflows/compensation-change-review-quality.yml` checks out the exact PR head, uses the repository's hash-pinned reviewed Python test toolchain, compiles source/tests, requires 100% package statement and branch coverage, and rejects checkout side effects.

## Ownership boundary

This slice adds no database migration, compensation calculation, payroll implementation, protected-attribute analytics, direct cross-service SQL, or competing People mutation surface. Authoritative Person/Employment/Assignment scope and subsequent HRIS mutation remain Orgmetra core responsibilities; external payroll work remains behind its published owner contract. UUIDv4 is an opacity/privacy constraint only and does not establish tenant membership, actor identity, worker relationship, or policy applicability. `docs/doctoring/compensation-change-review-references.md` records current primary-source context without promoting the package into a legal-compliance engine.
