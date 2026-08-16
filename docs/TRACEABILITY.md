# Traceability

| Requirement | Architecture | Data object | Test family | ADR |
|---|---|---|---|---|
| Separate person/employment/job/position/assignment | Core bounded contexts | `person_record`, `employment_record`, `job_profile`, `position_record`, `assignment_record` | schema/domain tests | ADR-0001 |
| Federated CWL integration | Integration Hub | `external_reference` conceptual | adapter contract tests | ADR-0002 |
| Effective/system time | Bitemporal HRIS | `effective_from`, `recorded_from` | bitemporal tests | ADR-0003 |
| Evidence-backed decisions | Talent Acquisition | `selection_decision`, `evidence_reference` | decision evidence tests | ADR-0001 |
| Predictive validity loop | Workforce Validation | `validity_study`, `criterion_observation` | validation registry tests | ADR-0001 |
| Purpose-bound PII access | Security architecture | field policy conceptual | authorization matrix tests | ADR-0003 |
| Least-privilege API capability | Keyverse gateway boundary | operation scope conceptual | scope and confused-deputy contract tests | ADR-0002 |
| Client-safe failure correlation | API error boundary | `support_reference` conceptual | error disclosure and support-lookup tests | ADR-0002 |
