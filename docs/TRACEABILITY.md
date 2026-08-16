# Traceability

| Requirement | Architecture | Data object | Test family | ADR |
|---|---|---|---|---|
| Separate person/employment/organization/job/position/assignment | Core bounded contexts + `orgmetra-domain` active PR | `person_record`, `employment_record`, `organization_unit`, `job_profile`, `position_record`, `assignment_record` | `test_domain.py` record and assignment tests | ADR-0001 |
| Durable organization/job identity with bitemporal descriptive history | People Core + `OrganizationUnitRecord` / `OrganizationUnitVersionRecord` / `JobProfileRecord` / `JobProfileVersionRecord` active PR | `organization_unit`, `organization_unit_version`, `job_profile`, `job_profile_version` | `RecordValidationTests` | ADR-0001, ADR-0003 |
| Effective/system time | Bitemporal HRIS + `BitemporalPeriod` active PR | `effective_from`, `effective_to`, `recorded_from`, `recorded_to` | `BitemporalPeriodTests` | ADR-0003 |
| Effective-known historical resolution | Bitemporal HRIS + `resolve_bitemporal_fact` active PR | version records exposing `BitemporalPeriod` | `BitemporalResolutionTests` retroactive-correction, no-match, aware-time and ambiguity cases | ADR-0003, ADR-0004 |
| Candidate-worker continuity | People Core + `CandidateWorkerRegistry` active PR | `candidate_worker_link` | `CandidateWorkerRegistryTests` | ADR-0001 |
| Federated CWL integration | Integration Hub | `external_reference` conceptual | adapter contract tests | ADR-0002 |
| Predictive validity loop | Workforce Validation | `validity_study`, `criterion_observation` | validation registry tests | ADR-0001 |
| Purpose-bound PII access | Security architecture | field policy conceptual | authorization matrix tests | ADR-0003 |
