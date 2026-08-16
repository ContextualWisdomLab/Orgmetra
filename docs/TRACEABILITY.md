# Traceability

| Requirement | Architecture | Data object | Test family | ADR |
|---|---|---|---|---|
| Separate person/employment/organization/job/position/assignment | Core bounded contexts + `orgmetra-domain` active PR | `person_record`, `employment_record`, `organization_unit`, `job_profile`, `position_record`, `assignment_record` | `test_domain.py` record and assignment tests | ADR-0001 |
| Durable organization/job identity with bitemporal descriptive history | People Core + `OrganizationUnitRecord` / `OrganizationUnitVersionRecord` / `JobProfileRecord` / `JobProfileVersionRecord` active PR | `organization_unit`, `organization_unit_version`, `job_profile`, `job_profile_version` | `RecordValidationTests` | ADR-0001, ADR-0003 |
| Durable employment/position identity with bitemporal status history | People Core + `EmploymentRecord` / `EmploymentVersionRecord` / `PositionRecord` / `PositionVersionRecord` active PR | `employment_record`, `employment_version`, `position_record`, `position_version` | `RecordValidationTests` plus covering-employment cases | ADR-0004, ADR-0006 |
| Effective/system time | Bitemporal HRIS + `BitemporalPeriod` active PR | `effective_from`, `effective_to`, `recorded_from`, `recorded_to` | `BitemporalPeriodTests` | ADR-0003 |
| Effective-known historical resolution | Bitemporal HRIS + identity-scoped resolvers active PR | version records exposing `BitemporalPeriod` | `BitemporalResolutionTests` and `IdentityScopedResolutionTests` | ADR-0003, ADR-0004, ADR-0006 |
| Recorded-time assignment correction | People Core + `validate_assignment_portfolio` active PR | `assignment_record` with `employment_record_id` and `numeric(5,4)` | `AssignmentRecordedTimeTests` A/A'/B correction triple | ADR-0006 |
| Multiple-membership staffing without atomistic collapse | People Core + person and position allocation sweeps | `assignment_record` | job-share and same-position conflict cases | ADR-0006 |
| Organization cycle rejection | Organization Core + `validate_organization_hierarchy` | `organization_unit_version.parent_organization_unit_id` | `OrganizationCycleTests` | ADR-0006 |
| Candidate-worker continuity without identifier leakage | People Core + `CandidateWorkerRegistry` active PR | `candidate_worker_link` | `CandidateWorkerRegistryTests` and `CandidateRelinkLeakageTests` | ADR-0001, ADR-0006 |
| Federated CWL integration | Integration Hub | `external_reference` conceptual | adapter contract tests | ADR-0002 |
| Predictive validity loop | Workforce Validation | `validity_study`, `criterion_observation` | validation registry tests | ADR-0001 |
| Purpose-bound PII access | Security architecture | field policy conceptual | authorization matrix tests | ADR-0003 |
