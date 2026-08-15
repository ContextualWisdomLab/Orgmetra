# Technical Requirements Document: Orgmetra

## 1. Technology baseline

- Monorepo with service boundaries.
- PostgreSQL for HRIS system of record.
- OpenAPI 3.2.0 for HTTP APIs.
- AsyncAPI/CloudEvents-style event envelopes for asynchronous integration.
- JSON Schema Draft 2020-12 for payload validation.
- Rust for future psychometric/mathematical production compute.
- TypeScript for web workspaces and gateway/BFF surfaces where appropriate.

## 2. Core services

| Service | Responsibility |
|---|---|
| `people_core` | Person, employment, candidate-worker linkage, identity references. |
| `organization_core` | Organization units, reporting relations, legal entities, locations. |
| `job_architecture` | Job profiles, tasks, FJA, KSAO, qualification rules, SME approvals. |
| `talent_acquisition` | Requisitions, candidates, evidence packets, interviews, decisions. |
| `performance_management` | Performance cycles, criterion blueprints, observations, calibration sessions. |
| `workforce_validation` | Validity studies, subgroup diagnostics, drift monitoring, selection utility. |
| `document_records` | Document metadata, source evidence, artifact references. |
| `audit_provenance` | Immutable audit and provenance graph. |
| `integration_hub` | CWL adapters and external HRIS migration adapters. |

## 3. API design

- Commands require idempotency keys.
- Mutating requests require actor, tenant, purpose, resource, and decision context.
- Read APIs enforce field-level authorization.
- High-impact decision APIs return evidence sufficiency status and escalation requirements.

## 4. Event envelope

```json
{
  "event_id": "uuidv7",
  "event_type": "selection_decision_recorded",
  "event_version": "1.0.0",
  "tenant_id": "tenant_reference",
  "subject_reference": "opaque_reference",
  "purpose_code": "selection_decision",
  "occurred_at": "business_event_time",
  "recorded_at": "system_record_time",
  "correlation_id": "workflow_reference",
  "causation_id": "preceding_event_reference",
  "provenance_reference": "evidence_reference",
  "data_classification": "restricted_hr"
}
```

## 5. Data model rules

- Use bitemporal validity for HR facts.
- Model multiple assignments with allocation ratios.
- Model entity roles as time-varying relations when external organizations can be customers, partners, competitors, or vendors in different contexts.
- Keep assessment results as external snapshot references unless Orgmetra explicitly owns the instrument lifecycle in a later ADR.

## 6. Integration adapters

- `keyverse_adapter`
- `naruon_adapter`
- `psychometrics_commons_adapter`
- `fast_mlsirm_adapter`
- `tepp_adapter`
- `semantic_data_portal_adapter`
- `contextual_orchestrator_adapter`
- `clearfolio_adapter`
- `newsdom_adapter`
- `mhtml_etl_adapter`
- `mightyetl_adapter`

Adapters must fail closed, never log credentials, and never promote external data to authoritative HRIS truth without Orgmetra command validation.

## 7. Testing requirements

- Unit tests for domain invariants.
- Migration tests for all DDL.
- API contract tests from OpenAPI schemas.
- Event contract tests.
- Authorization matrix tests for PII access.
- Bitemporal query tests.
- Candidate-worker linkage tests.
- Criterion and validation registry tests.
- Integration adapter fake-server tests.
- Accessibility tests for role workspaces.

## 8. Active implementation evidence

The stacked bitemporal domain slice implements these P0 contracts as a pure Python package:

- half-open effective and recorded intervals;
- timezone-aware system timestamps;
- distinct person, employment, and position records;
- multiple simultaneous assignments with total allocation no greater than one per person;
- append-only candidate-worker linkage;
- a PEP 561 typed-package marker;
- Python 3.11-3.14 CI, exact 100% production statement/branch coverage, and public docstring validation.

Psychometric and mathematical production arithmetic is intentionally absent from this package and remains Rust-first in its owning service.
