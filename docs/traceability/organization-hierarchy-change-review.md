# Organization hierarchy-change review traceability

## Truth classification

- **Protected-main truth:** Orgmetra owns bitemporal Organization Unit truth and historical hierarchy integrity on `develop`.
- **Active-PR truth:** this slice adds only a pre-mutation human-review packet for one Organization Unit parent change.
- **Not implemented by this slice:** durable hierarchy mutation, distributed uniqueness, authoritative actor resolution, database concurrency control, audit/outbox persistence, or an autonomous employment decision.

## Requirement matrix

| Requirement | Executable evidence | State |
|---|---|---|
| Keep Organization Unit parent review distinct from mutation authority | `test_builds_value_minimized_human_review_packet`, fixed `mutation_state=not_authorized_to_apply` | active_pr |
| Represent root attach/detach without a sentinel parent | `test_allows_attach_and_detach_root_transitions` | active_pr |
| Reject self-parenting and no-op parent changes before authoritative work | `test_rejects_ambiguous_hierarchy_or_actor_relationships` | active_pr |
| Preserve separate business and system-recorded time, and reject future system-recorded issuance | `test_accepts_fixed_offset_timestamp_and_canonicalizes_to_utc`, `test_rejects_noncanonical_temporal_primitives`, `test_rejects_future_system_recorded_time` | active_pr |
| Keep Person PII, worker values and employment decisions out of review evidence | `test_builds_value_minimized_human_review_packet`, direct-construction governance regressions | active_pr |
| Require accountable human separation and controlled purpose/reason | relationship regression plus invalid-trust-evidence and direct-construction regressions | active_pr |
| Preserve HRIS-owned UUID evolution while packet-owned correlations stay opaque UUIDv4 | `test_operational_organization_references_accept_uuid7`, invalid reference regressions | active_pr |
| Prevent caller polymorphism and low-level mutation from changing checked-versus-used issuance/export evidence | `test_rejects_caller_defined_runtime_subclasses`, `test_packet_runtime_type_integrity.py::test_rejects_packet_runtime_subclass_before_trust_field_validation`, `test_packet_runtime_type_integrity.py::test_rejects_subclass_that_bypasses_base_post_init`, `test_packet_runtime_type_integrity.py::test_rejects_representation_preserving_runtime_substitution_after_issuance`, `test_packet_runtime_type_integrity.py::test_issuance_validates_and_seals_one_snapshot_during_concurrent_mutation`, `test_packet_runtime_type_integrity.py::test_canonical_export_validates_and_emits_one_snapshot_during_concurrent_mutation`, `test_detects_post_construction_tampering_before_evidence_export` | active_pr |
| Make packet issuance single-use for one live object, including concurrent re-entry | `test_packet_runtime_type_integrity.py::test_rejects_manual_reissuance_after_reference_retargeting`, `test_packet_runtime_type_integrity.py::test_rejects_concurrent_reissuance_while_initial_issuance_is_in_progress` | active_pr |
| Prevent one still-live tenant-qualified review reference from identifying conflicting valid evidence | `test_live_reference_rejects_conflicting_reissuance` | active_pr |
| Require authoritative same-tenant bitemporal hierarchy verification, stale-parent/cycle/multiple-parent rejection and immutable audit/outbox before mutation | `test_next_action_preserves_authoritative_bitemporal_and_audit_boundary` | contract_only_in_this_slice |
| Exact installed-artifact quality after workflow consolidation | canonical `Foundation CI`: CPython 3.14.7, SHA-256-bound wheel install, package-owned pytest configuration requiring 100% statement/branch coverage, plus `test_repository_contract.py` preventing resurrection of the retired leaf workflow | active_pr |

## Protected-parent reconciliation

This active PR is reconciled onto protected `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`, which consolidated repository-owned quality execution into `.github/workflows/foundation-ci.yml`. The former `organization-hierarchy-change-review-quality.yml` leaf workflow is intentionally retired rather than resurrected. The package's exact installed-wheel test is executed by canonical Foundation CI, and the repository contract fails if that ownership moves back to the retired leaf or if the pinned CPython/wheel-hash/pytest execution contract disappears.

Historical checks from the pre-consolidation head do not transfer to the reconciled head. Only fresh workflow results bound to the exact reconciled commit are acceptance evidence.

## Boundary note

A passing packet proves only that review evidence satisfies this leaf contract. It does **not** prove that the current parent is still current, that the proposed parent is valid at the mutation coordinate, or that the resulting hierarchy is acyclic. Those facts must be re-established by the authoritative Orgmetra HRIS boundary immediately before any mutation and recorded with immutable audit/outbox evidence.

`recorded_at` is checked for issuance freshness only when the packet is created. Later canonical export validates the exact built-in temporal shape of the captured snapshot and its creation digest but does not re-enter wall-clock freshness, so a backward clock step cannot make already-issued evidence unreadable.

Caller-defined packet classes are rejected at subclass creation, before a subclass can replace `__post_init__`, `__getattribute__`, or another validation/emission hook. Exact primitive checks reject scalar runtime substitution at issuance. Because `frozen=True` is not an unforgeable runtime boundary against low-level `object.__setattr__`, issuance first captures every trust-bearing field once, applies the complete semantic validation contract to that captured snapshot, canonicalizes only those same values, and derives the creation digest plus live-reference key from that snapshot. The issuance concurrency regression pauses after the captured reason has been semantically checked, mutates the retained live object, and proves the mutated value cannot become the sealed reviewed evidence; a subsequent export rejects the changed live object against the creation digest.

Issuance is also single-use per live packet identity. Before validation begins, the registry atomically rejects an object that is already present in creation evidence or already owns an in-progress issuance reservation. This prevents a low-level-retargeted issued packet from calling `__post_init__()` again under a fresh valid change reference, and prevents two concurrent `__post_init__()` calls from both attempting to seal the same object. The reservation is process-local defense in depth and is released after a failed first issuance; it is not durable uniqueness or cross-process authorization.

Canonical export independently captures every trust-bearing field once, validates exact runtime types on those captured values, and serializes only those same values. The representation-preserving subtype regression proves pre-capture substitution fails closed; the export concurrent-mutation regression proves a mutation after capture cannot alter the evidence selected for that export, while a later export still detects the changed semantic value against the issuance digest.

Keeping an unreachable base packet-type branch after subclass creation was sealed would violate the package's owned 100% coverage contract, so packet-class finality lives at class creation. Scalar representation integrity, issuance snapshot integrity, single-use issuance and checked-snapshot export are separate executable invariants because a frozen instance can still be modified or re-entered through low-level Python primitives.

The live-reference registry is process-local defense in depth. It prevents conflicting in-process reissuance while an idempotent packet remains alive, but it does not replace durable tenant-qualified uniqueness or immutable persistence across processes/restarts. The authoritative persistence/audit transaction owns those guarantees.
