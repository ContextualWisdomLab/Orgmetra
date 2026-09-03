# Candidate application core traceability

- **Maturity:** `implemented_on_active_pr`
- **Protected-main gap:** `candidate_profile.application_status_code` is one unscoped status on candidate identity
- **Buyer capability:** Multi-opening candidate application lifecycle with tenant-safe bitemporal Job/Position scope
- **Owned persistence:** `candidate_application_record`, `candidate_application_record_version`, `candidate_application_stage_record`

| Requirement | Evidence |
|---|---|
| Separate candidate identity from application lifecycle | `0014_candidate_application_core.sql` creates one durable application anchor per candidate/requisition, separate bitemporal opening-scope versions, and bitemporal stage facts; the legacy profile status is retained only for compatibility |
| Preserve one durable application identity across corrections | `candidate_application_record` is immutable and has no `recorded_to`; `candidate_application_record_version` carries correctable Job/Position scope. The PostgreSQL regression closes version `...071`, appends replacement version `...074`, and requires the durable application ID `...051` to remain unchanged |
| Keep stage lineage attached to the stable application | Every `candidate_application_stage_record` references `(tenant_record_id, candidate_application_record_id)` on the immutable anchor. `test_candidate_application_decision_boundary_postgres.sh` fails if a stage row lacks its stable application anchor |
| Support one candidate pursuing multiple openings | PostgreSQL regression inserts two application anchors for one candidate against two distinct requisition contexts and requires both to remain visible |
| Preserve Job, Position and application semantics | Mutable opening scope lives on `candidate_application_record_version`; optional Position uses tenant-qualified `(tenant_record_id, position_record_id, job_profile_id)` FK so a seat cannot be paired with another Job |
| Preserve tenant isolation structurally and at runtime | Composite tenant FKs reject foreign candidate/Job/Position identities; all three application relations force PostgreSQL RLS through `current_tenant_record_id()`. `test_candidate_application_rls_postgres.sh` uses a `NOBYPASSRLS` role to prove missing context exposes zero rows, tenant Alpha sees tenant-local anchor/version/stage evidence, tenant Beta cannot observe Alpha history, and a cross-tenant INSERT is rejected by the policy `WITH CHECK` path |
| Use opaque public/correlation identifiers | Application, scope-version and stage IDs are operational UUIDs with nil/max sentinels rejected; requisition correlation is canonical `requisition:<uuid>` and contains no human-readable requisition title |
| Preserve effective/business and system-recorded time | The immutable anchor preserves submission/system creation time. Scope versions and stage facts preserve effective and recorded half-open intervals with strict non-empty checks |
| Prevent contradictory opening-scope truth | `candidate_application_version_bitemporal_exclusion` rejects overlapping effective+recorded scope versions for one stable application while adjacent recorded correction intervals remain valid; regression covers both cases |
| Prevent contradictory historical stage truth | `candidate_application_stage_bitemporal_exclusion` rejects simultaneous effective+recorded overlap for one application; the regression exercises the exclusion |
| Preserve correction evidence instead of rewriting history | `protect_bitemporal_history()` guards scope-version and stage relations. Regression proves mutable scope correction closes only `recorded_to` on version `...071`, appends replacement version `...074` at the boundary under the same application anchor, rejects an overlapping replacement, and separately proves stage mutation fails before append-only correction |
| Keep high-impact employment outcomes human-governed | Raw stage vocabulary contains only `received`, `screening`, `assessment`, `interview`, and `offer_pending`; core regression proves `hired` is rejected and `test_candidate_application_decision_boundary_postgres.sh` proves ambiguous `closed` is rejected. Final employer outcome remains the existing `selection_decision` human-confirmation/evidence boundary |
| Require provenance before treating withdrawal as candidate-driven | Bare `withdrawn` is rejected by `test_candidate_application_decision_boundary_postgres.sh`; the slice has no authoritative initiating-actor/withdrawal-evidence field yet, so it fails closed rather than allowing staff to encode a shadow rejection as candidate withdrawal |
| Keep administrative opening closure out of candidate outcomes | Generic `closed` is not a candidate stage; requisition/opening closure belongs to the opening lifecycle so it cannot masquerade as candidate-specific rejection without governed selection evidence |
| Prevent bulk history erasure | Anchor/version/stage relations have TRUNCATE guards or immutable-anchor mutation guards, public TRUNCATE revocation and row-level history protection; regressions exercise version/stage TRUNCATE rejection |
| Minimize PII | New persistence stores opaque candidate/application/requisition/Job/Position identifiers and workflow metadata only; it does not copy names, contact data, demographic fields, assessment values, résumé content or model output |
| Preserve requisition ownership boundary | `requisition_reference` correlates to the governed Orgmetra requisition-review contract but does not reach into another service or treat a packet as mutable application state |
| Verify exact PR head and ordered fixture dependencies | `.github/workflows/candidate-application-quality.yml` pins checkout action, proves `git rev-parse HEAD`, runs the primary schema/fixture contract first, then the decision and `NOBYPASSRLS` contracts against that same PostgreSQL service, and finally proves validation left the tree unchanged |

## Standards/research decision evidence

The modeling decision is informed by current published ISO 30201:2026 HR management-system requirements, ISO 30405:2023 recruitment guidance, HR Open Standards' approved Recruiting 4.2 distinction between the official `Candidate` and `PositionOpening` objects, and the current HR Open Recruiting project's application-form/talent-pipeline scope. Exact APA 7 references and retrieval/verification dates are in `docs/doctoring/candidate-application-references.md`.

## Claims intentionally not made

This active PR does **not** claim protected-main availability, a complete applicant-tracking product, final requisition persistence, candidate-facing UI, selection-decision-to-application persistence, a governed candidate-withdrawal event, migrated legacy profile statuses, deployed API behavior, certification to ISO 30201/30405, or any HR Open Standards certification. Those remain separate acceptance surfaces.
