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
| Preserve separate business and system-recorded time | `test_accepts_fixed_offset_timestamp_and_canonicalizes_to_utc`, `test_rejects_noncanonical_temporal_primitives` | active_pr |
| Keep Person PII, worker values and employment decisions out of review evidence | `test_builds_value_minimized_human_review_packet`, direct-construction governance regressions | active_pr |
| Require accountable human separation and controlled purpose/reason | relationship regression plus invalid-trust-evidence and direct-construction regressions | active_pr |
| Preserve HRIS-owned UUID evolution while packet-owned correlations stay opaque UUIDv4 | `test_operational_organization_references_accept_uuid7`, invalid reference regressions | active_pr |
| Prevent caller polymorphism and post-construction rewriting from changing checked-vs-emitted evidence | `test_rejects_caller_defined_runtime_subclasses`, `test_detects_post_construction_tampering_before_evidence_export` | active_pr |
| Prevent one still-live tenant-qualified review reference from identifying conflicting valid evidence | `test_live_reference_rejects_conflicting_reissuance` | active_pr |
| Require authoritative same-tenant bitemporal hierarchy verification, stale-parent/cycle/multiple-parent rejection and immutable audit/outbox before mutation | `test_next_action_preserves_authoritative_bitemporal_and_audit_boundary` | contract_only_in_this_slice |
| Exact installed-artifact quality | dedicated workflow: CPython 3.14.7, SHA-256-bound wheel, 100% owned statement/branch coverage, clean checkout | active_pr |

## Boundary note

A passing packet proves only that review evidence satisfies this leaf contract. It does **not** prove that the current parent is still current, that the proposed parent is valid at the mutation coordinate, or that the resulting hierarchy is acyclic. Those facts must be re-established by the authoritative Orgmetra HRIS boundary immediately before any mutation and recorded with immutable audit/outbox evidence.

The live-reference registry is process-local defense in depth. It prevents conflicting in-process reissuance while an idempotent packet remains alive, but it does not replace durable tenant-qualified uniqueness or immutable persistence across processes/restarts. The authoritative persistence/audit transaction owns those guarantees.
