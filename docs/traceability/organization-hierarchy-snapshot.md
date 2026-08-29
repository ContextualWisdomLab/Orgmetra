# Organization hierarchy snapshot traceability

## Scope and maturity

| Capability | Maturity | Evidence | Buyer boundary |
| --- | --- | --- | --- |
| Resolve one tenant's organization parent links at an effective date and recorded-time cutoff | `implemented_on_active_pr` | `packages/hris-kernel/src/orgmetra_hris_kernel/organization.py` | Historical structure reconstruction only |
| Reject contradictory visible parent versions | `implemented_on_active_pr` | `resolve_single_valued_fact(...)`; `test_builder_rejects_two_visible_parent_versions_for_one_unit` | Correct authoritative bitemporal facts before export |
| Reject visible organization cycles | `implemented_on_active_pr` | shared `_require_acyclic_parent_links(...)`; existing and snapshot cycle regressions | Does not infer or repair reporting lines |
| Emit deterministic opaque hierarchy evidence | `implemented_on_active_pr` | `OrganizationHierarchySnapshot.canonical_json()` / `content_digest()` | Tenant/unit UUIDs, coordinate, and structural counts only |
| Purpose-bound API authorization and UI presentation | `planned` | Existing Orgmetra authorization/UI boundaries | Snapshot alone grants no access or employment authority |

`implemented_on_active_pr` means the capability exists only on the active Orgmetra branch until the exact head earns required checks, review, protected merge, and any release evidence. It must not be described as protected-branch or released truth before then.

## Requirements mapped to tests

| Requirement | Regression |
| --- | --- |
| Foreign-tenant and future-recorded facts cannot leak into the requested snapshot | `test_snapshot_exposes_only_visible_tenant_structure_with_deterministic_evidence` |
| Input ordering cannot change evidence bytes or digest | `test_snapshot_is_independent_of_input_version_order` |
| A timezone-naive knowledge cutoff fails closed even for empty input | `test_builder_rejects_naive_cutoff_even_when_no_units_are_visible` |
| Mutable, unrepresentable, or provider-controlled knowledge cutoffs cannot rewrite evidence | `test_snapshot_detaches_mutable_timezone_before_canonicalization`; temporal-integrity regressions |
| Public snapshot construction cannot bypass awareness, unique-unit, canonical-order, or acyclic-graph invariants | `test_direct_snapshot_rejects_*` |
| Two simultaneously visible versions for one organization unit fail closed | `test_builder_rejects_two_visible_parent_versions_for_one_unit` |
| Opaque parent anchors missing from the visible coordinate are retained rather than silently promoted to roots | deterministic parent-link assertion in the primary snapshot regression |

The listed structural regressions are in `packages/hris-kernel/tests/test_organization_hierarchy_snapshot.py`; temporal hardening is in `packages/hris-kernel/tests/test_organization_hierarchy_temporal_integrity.py`. The existing `Workforce Intelligence Quality` workflow runs the complete HRIS kernel with exact statement and branch coverage requirements whenever `packages/hris-kernel/**` changes.

## Data and decision boundary

The snapshot intentionally carries no Person, Employment, Assignment, compensation, protected-attribute, credential, or free-form descriptive values. Organization-unit identifiers remain tenant-sensitive opaque business references and require the host's purpose-bound authorization before presentation or export. The snapshot does not establish managerial authority, legal-entity relationships, span-of-control policy, worker allocation, or a high-impact employment decision.

The implementation composes the protected bitemporal contract in ADR 0003 with the existing organization-cycle invariant. It does not introduce a second organization system of record, a third temporal dimension, cross-service SQL, or a dedicated-writer dependency mutation.

## Standards evidence

Current primary standards evidence is recorded in `docs/doctoring/organization-hierarchy-snapshot-references.md`. ISO 30201:2026, ISO 30400:2022, and ISO 30414:2025 inform terminology, controlled HR-management-system evidence, and human-capital reporting context. This traceability record does **not** claim ISO conformity or certification.
