# Traceability

## 2. Product traceability matrix

| Requirement | Architecture | Data object | Test family | ADR | Maturity |
|---|---|---|---|---|---|
| Separate person/employment/organization/job/position/assignment | Core bounded contexts | `person_record`, `employment_record`, `employment_record_version`, `organization_unit`, `job_profile`, `position_record`, `position_record_version`, `assignment_record` | schema/domain and `orgmetra_hris_kernel` tests | ADR-0001, ADR-0004, ADR-0005 | implemented_on_active_pr |
| Exclusive employment and staffable seats | Core bounded contexts | `employment_concurrency_code`, staffable `position_status_code`, assignment allocation totals | Memorial Hospital exclusivity, freeze, and seat-capacity kernel tests plus OpenAPI employment/position/assignment commands | ADR-0005 | implemented_on_active_pr |
| Tenant-qualified HRIS integrity and fail-closed row isolation | Core bounded contexts / Security architecture | `tenant_record`, tenant-qualified foreign keys, forced row-level security policies | PostgreSQL cross-tenant FK and application-role RLS contract | ADR-0001, ADR-0003 | implemented_on_active_pr |
| Normalized bitemporal organization/job/employment/position history | Core bounded contexts | `organization_unit_version`, `job_profile_version`, `employment_record_version`, `position_record_version` | PostgreSQL non-overlap, concurrent conflict, correction, rewrite-rejection, and assignment-employment binding | ADR-0001, ADR-0003, ADR-0004 | implemented_on_active_pr |
| Effective/system time | Bitemporal HRIS | `effective_from`, `recorded_from` | strict half-open interval and historical-coordinate tests | ADR-0003 | implemented_on_active_pr |
| Evidence-backed human selection decisions | Talent Acquisition | `decision_evidence_set`, `selection_decision_evidence`, `selection_decision` | database-owned SHA-256 sealing, non-empty evidence, drift/reuse rejection, OpenAPI human-confirmation tests | ADR-0001 | implemented_on_active_pr |
| Predictive-validity evidence lineage | Workforce Validation | `validity_study`, `validity_study_decision_link`, `validity_study_evidence_set_link`, `validity_study_outcome_link`, `criterion_observation` | normalized linkage and append-only database contract; statistical validation remains subsequent work | ADR-0001 | implemented_on_active_pr |
| Purpose-bound PII access | Security architecture | field policy conceptual | authorization matrix tests | ADR-0003 | accepted_architecture |
| Least-privilege API capability | Keyverse gateway boundary | operation scope conceptual | structural per-operation scope and confused-deputy contract tests | ADR-0002 | implemented_on_active_pr |
| Client-safe failure correlation | API error boundary | `support_reference` conceptual | error disclosure and support-lookup tests | ADR-0002 | implemented_on_active_pr |
| Foundation artifact integrity | Repository governance | deterministic `manifest.json` file inventory | SHA-256/byte/line validation plus Python/Node inventory-equivalence regression | ADR-0001 | implemented_on_active_pr |

## 4. CWL integration traceability

| External contract | Orgmetra owner boundary | Integration style | Required evidence | ADR | Maturity |
|---|---|---|---|---|---|
| Keyverse identity and authorization | API Gateway / purpose-bound authorization | Published OIDC/API contract plus `orgmetra_keyverse_adapter` subject binding | tenant, actor, purpose, scope, opaque subject, no stored credentials | ADR-0002 | implemented_on_active_pr |
| naruon communication and calendar | Integration Hub | Published API/event adapter | idempotency, delivery audit, no direct table access | ADR-0002 | planned |
| Psychometrics Commons @ `cc5850a0d1eacbbf16d03075534fce460a8286e6` | Workforce Validation | Immutable response/result snapshot contract | pinned revision, model/version/provenance snapshot, immutable result linkage, no direct application-table access | ADR-0002 | accepted_architecture |
| fast-mlsirm @ `fb67ced09d8ee00542c05d56374537a9a7239751` | Workforce Validation | Published `orgmetra.fast_mlsirm.v1` result contract; direct calls only from approved offline validation worker | pinned revision, contract identifier, backend/result provenance, CPU/GPU parity evidence where material, no duplicated kernel | ADR-0002 | accepted_architecture |
| TEPP temporal evidence | Workforce Validation | Published package/API contract | temporal provenance and version binding | ADR-0002 | planned |
| MHTML ETL Gateway / mightyETL | Governed Migration | Published ETL contract | lineage, idempotency, reconciliation, rollback | ADR-0002 | planned |
| Semantic Data Portal / OriginWeave / LineageWeave | Evidence and lineage adapters | Published API/event contracts | provenance, tenant ACL, retention, export controls | ADR-0002 | planned |
| contextual-orchestrator | Draft-evidence orchestration adapter | Published API contract | model provenance, untrusted-output labeling, human confirmation | ADR-0002 | planned |
