# Position reporting-change review traceability

**Status:** active PR / proposed capability. Not protected-main truth until merged from one fully validated exact head.

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
| Exact 100% owned statement/branch coverage and installed artifact truth | dedicated workflow builds one exact wheel, hash-binds installation, tests pinned CPython 3.14.7 and requires clean checkout | `.github/workflows/position-reporting-change-review-quality.yml` |
| Governance docs cannot bypass the focused gate | workflow path filter includes ADR, doctoring and traceability | `test_quality_workflow_covers_all_governed_docs` |

The packet deliberately cannot prove that the current reporting edge exists, that a proposed manager is authorized or legally permissible, or that persistence succeeded. Those remain authoritative HRIS/runtime/policy evidence and must not be inferred from a packet digest.
