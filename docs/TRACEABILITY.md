# Traceability

## 2. Product traceability matrix

| Requirement | Architecture | Data object | Test family | ADR | Maturity |
|---|---|---|---|---|---|
| Separate person/employment/organization/job/position/assignment | Core bounded contexts | `person_record`, `employment_record`, `organization_unit`, `job_profile`, `position_record`, `assignment_record` | schema/domain tests | ADR-0001 | implemented_on_active_pr |
| Normalized bitemporal organization/job history | Core bounded contexts | `organization_unit_version`, `job_profile_version` | foundation database contract validation | ADR-0001, ADR-0003 | implemented_on_active_pr |
| Effective/system time | Bitemporal HRIS | `effective_from`, `recorded_from` | strict half-open interval tests | ADR-0003 | implemented_on_active_pr |
| Evidence-backed decisions | Talent Acquisition | `selection_decision`, `selection_decision_evidence` | decision evidence tests | ADR-0001 | implemented_on_active_pr |
| Predictive validity loop | Workforce Validation | `validity_study`, `criterion_observation` | validation registry tests | ADR-0001 | accepted_architecture |
| Purpose-bound PII access | Security architecture | field policy conceptual | authorization matrix tests | ADR-0003 | accepted_architecture |
| Least-privilege API capability | Keyverse gateway boundary | operation scope conceptual | scope and confused-deputy contract tests | ADR-0002 | implemented_on_active_pr |
| Client-safe failure correlation | API error boundary | `support_reference` conceptual | error disclosure and support-lookup tests | ADR-0002 | implemented_on_active_pr |

## 4. CWL integration traceability

| External contract | Orgmetra owner boundary | Integration style | Required evidence | ADR | Maturity |
|---|---|---|---|---|---|
| Keyverse identity and authorization | API Gateway / purpose-bound authorization | Published OIDC/API contract | tenant, actor, purpose, scope, denial audit | ADR-0002 | accepted_architecture |
| naruon communication and calendar | Integration Hub | Published API/event adapter | idempotency, delivery audit, no direct table access | ADR-0002 | planned |
| Psychometrics Commons / fast-mlsirm | Workforce Validation | Immutable result/provenance contract | model/version/provenance snapshot; no duplicated kernel | ADR-0002 | accepted_architecture |
| TEPP temporal evidence | Workforce Validation | Published package/API contract | temporal provenance and version binding | ADR-0002 | planned |
| MHTML ETL Gateway / mightyETL | Governed Migration | Published ETL contract | lineage, idempotency, reconciliation, rollback | ADR-0002 | planned |
| Semantic Data Portal / OriginWeave / LineageWeave | Evidence and lineage adapters | Published API/event contracts | provenance, tenant ACL, retention, export controls | ADR-0002 | planned |
| contextual-orchestrator | Draft-evidence orchestration adapter | Published API contract | model provenance, untrusted-output labeling, human confirmation | ADR-0002 | planned |
