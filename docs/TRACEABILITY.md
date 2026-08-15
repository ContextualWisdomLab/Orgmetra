# Traceability

| Requirement | Architecture | Data object | Test family | ADR |
|---|---|---|---|---|
| Separate person/employment/job/position/assignment | Core bounded contexts + `orgmetra-domain` active PR | `person_record`, `employment_record`, `job_profile`, `position_record`, `assignment_record` | `test_domain.py` record and assignment tests | ADR-0001 |
| Federated CWL integration | Integration Hub | `external_reference` conceptual | adapter contract tests | ADR-0002 |
| Effective/system time | Bitemporal HRIS + `BitemporalPeriod` active PR | `effective_from`, `recorded_from` | `BitemporalPeriodTests` | ADR-0003 |
| Candidate-worker continuity | People Core + `CandidateWorkerRegistry` active PR | `candidate_worker_link` | `CandidateWorkerRegistryTests` | ADR-0001 |
| Predictive validity loop | Workforce Validation | `validity_study`, `criterion_observation` | validation registry tests | ADR-0001 |
| Purpose-bound PII access | Security architecture | field policy conceptual | authorization matrix tests | ADR-0003 |
