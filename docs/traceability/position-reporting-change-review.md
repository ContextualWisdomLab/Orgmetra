# Position reporting-change review traceability

**Status:** active PR / proposed capability. Not protected-main truth until merged from one fully validated exact head.

## Current protected-parent adoption

Feature predecessor `adf055d79d188ba18d06ecf80dc1117858c987f4` was non-destructively reconciled with protected `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f` by ordinary two-parent adoption commit `2317c367aa200e2cd1636cc26dd96c8b01966804`. The resulting tree preserves the protected #161 repository-workflow consolidation and does not import mutable #94 source. Historical checks on the predecessor remain causal evidence only; the resulting successor must reacquire all applicable exact-head gates before Ready or merge.

Fresh Foundation execution on successor `c0975db9f976fda93696591ac04a9787cde4aef5` exposed a repository-workflow reconciliation RED before package tests: the feature tree had resurrected its package-local quality workflow with `runs-on: ubuntu-latest`, violating protected #161's exact `ubuntu-24.04` runner and two-local-workflow inventory contract. The repair keeps the leaf retired and moves its exact installed-wheel, hash-bound installation, pinned CPython 3.14.7 and 100% coverage contract into canonical one-job Foundation CI.

| Requirement | Design / implementation evidence | Executable evidence |
|---|---|---|
| Keep reporting authority attached to Position rather than Person | Packet carries subordinate/current-manager/proposed-manager `position_record:` references and no Person identifier | `test_builds_value_minimized_human_review_packet`, `test_operational_position_references_accept_uuid7` |
| Preserve authoritative identifier ownership | Tenant and Position references accept canonical non-sentinel operational UUIDs; leaf-owned change and actor references require canonical UUIDv4 | invalid trust-evidence matrix plus UUIDv7 interoperability regression |
| Keep review separate from mutation authority | Fixed `mutation_state=not_authorized_to_apply`, `decision_authority=human_review_only`, mandatory human review | `test_direct_construction_cannot_weaken_governance` |
| Require authoritative bitemporal scope before mutation | Fixed `requires_authoritative_resolution`; next action requires exact tenant, `effective_on`, current system-recorded cutoff, Position validity/staffability and current relationship resolution | `test_next_action_preserves_authoritative_bitemporal_and_audit_boundary` |
| Prevent obvious invalid reporting proposals | subordinate/current/proposed Position references must be pairwise different | `test_rejects_ambiguous_reporting_or_actor_relationships` |
| Require authoritative cycle/cardinality checks | next action explicitly rejects cycles and multiple visible solid-line managers before mutation | `test_next_action_preserves_authoritative_bitemporal_and_audit_boundary` |
| Separate requester and reviewer | identical actor references are rejected locally; next action still requires authoritative identity separation | ambiguous relationship regression and next-action regression |
| Minimize durable privacy surface | no Person identifier, worker value, compensation, rating or free-form reason; controlled reason vocabulary only | value-minimization regression and invalid reason matrix |
| Preserve business time vs system-recorded time | exact `effective_on` date is distinct from exact fixed-offset `recorded_at`, canonicalized to UTC | fixed-offset and noncanonical temporal regressions |
| Bind reviewed organizational evidence | Position-scope and organization-scope snapshots require lowercase SHA-256 digests | invalid digest matrix and deterministic canonical-evidence regression |
| Prevent checked-vs-emitted runtime forgery | exact built-in text/int/date/datetime primitives and creation-time canonical seal | hostile runtime-subclass regressions and post-construction tamper regression |
| Require immutable audit/outbox before mutation | next action routes only after authoritative resolution and requires immutable audit/outbox evidence | next-action regression |
| Exact 100% owned statement/branch coverage and installed artifact truth | canonical Foundation builds one exact wheel, hash-binds installation, uses pinned CPython 3.14.7 and executes the package suite under its unchanged 100% statement/branch threshold | `.github/workflows/foundation-ci.yml`; `test_repository_contract.py` |
| Governance-only edits still enter required validation | canonical Foundation triggers for every pull request to `develop`; the package regression keeps the retired leaf from returning and pins the installed-artifact step | `test_canonical_foundation_executes_installed_artifact_contract` |

The packet deliberately cannot prove that the current reporting edge exists, that a proposed manager is authorized or legally permissible, or that persistence succeeded. Those remain authoritative HRIS/runtime/policy evidence and must not be inferred from a packet digest.
