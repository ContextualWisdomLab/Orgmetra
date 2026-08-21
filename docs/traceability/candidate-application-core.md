# Candidate application core traceability

- **Maturity:** `implemented_on_active_pr`
- **Protected-main gap:** `candidate_profile.application_status_code` is one unscoped status on candidate identity
- **Buyer capability:** Multi-opening candidate application lifecycle with tenant-safe Job/Position context
- **Owned persistence:** `candidate_application_record`, `candidate_application_stage_record`

| Requirement | Evidence |
|---|---|
| Separate candidate identity from application lifecycle | `0014_candidate_application_core.sql` creates one durable application identity per candidate/requisition and bitemporal stage facts; the legacy profile status is retained only for compatibility |
| Support one candidate pursuing multiple openings | PostgreSQL regression inserts two current application identities for one candidate against two distinct requisition/Job/Position contexts and requires both to remain visible |
| Preserve Job, Position and application semantics | Application stores the Job explicitly; optional Position uses tenant-qualified `(tenant_record_id, position_record_id, job_profile_id)` FK so a seat cannot be paired with another Job |
| Preserve tenant isolation structurally and at runtime | Composite tenant FKs reject foreign candidate/Job/Position identities; both application relations force PostgreSQL RLS through `current_tenant_record_id()` |
| Use opaque public/correlation identifiers | Application and stage IDs are operational UUIDs with nil/max sentinels rejected; requisition correlation is a bounded canonical `requisition:<uuid>` reference and contains no human-readable requisition title |
| Preserve effective/business and system-recorded time | Application anchors preserve submission time plus recorded interval; stage facts preserve effective and recorded half-open intervals with strict non-empty checks |
| Prevent contradictory historical stage truth | `candidate_application_stage_bitemporal_exclusion` rejects simultaneous effective+recorded overlap for one application; the regression exercises the exclusion |
| Preserve correction evidence instead of rewriting history | Existing `protect_bitemporal_history()` guards both relations; regression proves stage mutation fails, closes one recorded interval, then appends replacement knowledge at the boundary |
| Keep high-impact employment outcomes human-governed | Stage vocabulary excludes `hired` and `rejected`; regression proves `hired` is rejected. Final employer outcome remains the existing `selection_decision` human-confirmation/evidence boundary |
| Prevent bulk history erasure | Both relations have BEFORE TRUNCATE guards, public TRUNCATE revocation and row-level mutation guards; regression proves stage history cannot be truncated |
| Minimize PII | New persistence stores candidate/application/requisition/Job/Position identifiers and workflow metadata only; it does not copy names, contact data, demographic fields, assessment values, résumé content or model output |
| Preserve requisition ownership boundary | `requisition_reference` correlates to the governed Orgmetra requisition-review contract but does not reach into another service or treat a packet as mutable application state |
| Verify exact PR head | `.github/workflows/candidate-application-quality.yml` pins checkout action, proves `git rev-parse HEAD`, runs the PostgreSQL regression on pinned PostgreSQL 16.14, then proves the validation left the tree unchanged |

## Standards/research decision evidence

The modeling decision is informed by the current published ISO 30201:2026 HR management-system requirements, ISO 30405:2023 recruitment guidance, HR Open Standards' approved Recruiting 4.2 distinction between Candidate Record and Position Opening, and the current HR Open Recruiting workgroup's explicit application-form/talent-pipeline scope. Exact APA 7 references and retrieval/verification dates are in `docs/doctoring/candidate-application-references.md`.

## Claims intentionally not made

This active PR does **not** claim protected-main availability, a complete applicant-tracking product, final requisition persistence, candidate-facing UI, selection-decision-to-application persistence, migrated legacy profile statuses, deployed API behavior, certification to ISO 30201/30405, or any HR Open Standards certification. Those remain separate acceptance surfaces.
