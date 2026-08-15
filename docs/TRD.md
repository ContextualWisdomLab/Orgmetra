# Technical Requirements Document: Orgmetra

## 1. Technology baseline

- Monorepo with explicit service boundaries.
- PostgreSQL for the HRIS system of record, physically shareable only through service-owned schemas and database roles.
- OpenAPI 3.2.0 for HTTP APIs.
- AsyncAPI/CloudEvents-style event envelopes for asynchronous integration.
- JSON Schema Draft 2020-12 for payload validation.
- TypeScript for web workspaces and gateway/BFF surfaces where appropriate.
- Rust for mathematical and psychometric production compute.

Material mathematical and psychometric kernels must use bounded CPU multithreading with a fixed worker pool and documented oversubscription controls. A GPU backend is required when profiling shows material buyer benefit or a product requirement names GPU execution. The GPU result must be compared with the CPU `f64` reference across deterministic fixtures, simulated true parameters, edge cases, and production-sized benchmarks. Each kernel publishes tolerances for objective value, estimates, gradients, uncertainty, convergence, and failure classification; skipped or unavailable GPU execution cannot be reported as parity success.

## 2. Core services

| Canonical service identifier | Responsibility |
|---|---|
| `people_core` | Person identity anchors, names, employment, assignments, compensation, candidate-worker linkage, and identity references. |
| `organization_core` | Organization units, reporting relations, legal entities, locations, and positions. |
| `job_architecture` | Job profiles, tasks, FJA, KSAO, qualification rules, evidence, and SME approvals. |
| `talent_acquisition` | Requisitions, candidates, evidence packets, interviews, confirmations, and selection decisions. |
| `performance_management` | Performance cycles, criterion blueprints, observations, and calibration sessions. |
| `workforce_validation` | Validity studies, subgroup diagnostics, drift monitoring, selection utility, and scientific adapters. |
| `document_records` | Document metadata, source evidence, and immutable artifact references. |
| `audit_provenance` | Immutable audit and provenance graph. |
| `integration_hub` | CWL adapters, inbox/outbox state, and external HRIS migration adapters. |

These identifiers are canonical across deployment names, ACLs, metrics, generated clients, schemas, and event ownership. Display labels may use title case but cannot create a second service identity.

## 3. API design

- Commands require idempotency keys.
- Mutating requests require authenticated actor, tenant, purpose, resource, and decision context.
- Read APIs enforce tenant and field-level authorization.
- High-impact commands require previewed and recorded reason, confirmation, and exact evidence versions.
- High-impact decision APIs return evidence sufficiency and escalation status.
- Generated server validation must enforce the OpenAPI contract before domain handlers execute.

## 4. Event envelope

```json
{
  "event_id": "uuidv7",
  "event_type": "selection_decision_recorded",
  "event_version": "1.0.0",
  "tenant_id": "tenant_reference",
  "subject_reference": "opaque_reference",
  "actor_reference": "opaque_actor_reference",
  "purpose_code": "selection_decision",
  "occurred_at": "business_event_time",
  "recorded_at": "system_record_time",
  "correlation_id": "workflow_reference",
  "causation_id": "preceding_event_reference",
  "provenance_reference": "audit_and_evidence_bundle_reference",
  "data_classification": "restricted_hr"
}
```

`actor_reference` is required and resolves only inside the authorized tenant. `provenance_reference` is also required and resolves to an immutable audit bundle containing actor, policy decision, confirmation, reason, command digest, and evidence versions. Consumers must verify both fields before treating a high-impact event as accountable.

## 5. Data model rules

- Stable entity anchors do not contain mutable descriptive attributes.
- Versioned HR facts keep effective time and system-recorded time separately.
- The database rejects reversed temporal intervals.
- Model multiple assignments with allocation ratios.
- Model external organization roles as time-varying relations when one entity can be a customer, partner, competitor, or vendor in different contexts.
- Keep assessment results as external immutable snapshot references unless a later ADR transfers instrument lifecycle ownership.
- Selection decisions, their evidence references, and candidate-worker links are append-only.

## 6. Integration adapters

| Adapter | Target and contract | Owner |
|---|---|---|
| `keyverse_adapter` | Keyverse OIDC/SCIM contract | `integration_hub` |
| `naruon_adapter` | Naruon communication-intent contract | `integration_hub` |
| `psychometrics_commons_adapter` | immutable response/result snapshot contract pinned to `cc5850a0d1eacbbf16d03075534fce460a8286e6` | `workforce_validation` |
| `fast_mlsirm_adapter` | `orgmetra.fast_mlsirm.v1`, repository `ContextualWisdomLab/fast-mlsirm` pinned to `fb67ced09d8ee00542c05d56374537a9a7239751`; online role workspaces consume it through Psychometrics Commons, while direct calls are limited to an approved offline validation worker | `workforce_validation` |
| `tepp_adapter` | `orgmetra.tepp.v1`, repository `ContextualWisdomLab/TEPP` pinned to `40adac9a26a8af85147ffa2795fb548ea243e0e5` | `workforce_validation` |
| `semantic_data_portal_adapter` | versioned ontology and data-catalog contract | `job_architecture` |
| `contextual_orchestrator_adapter` | schema-bound draft and verification operations; no authoritative writes | `job_architecture` and `integration_hub` |
| `clearfolio_adapter` | document preview artifact contract | `document_records` |
| `newsdom_adapter` | canonical document-block and source-span contract | `document_records` |
| `mhtml_etl_adapter` | governed schema-proposal and row-lineage contract | `integration_hub` |
| `mightyetl_adapter` | bounded migration/CDC contract | `integration_hub` |

Adapters use bounded timeouts, typed error semantics, tenant validation, idempotency, and provenance. They fail closed, never log credentials, and never promote external data to authoritative HRIS truth without Orgmetra command validation.

## 7. Testing requirements

`docs/TEST_STRATEGY.md` is the canonical coverage and execution contract. Every service must satisfy its 100% statement/branch coverage requirement where the pinned toolchain exposes those metrics, document exact commands, and preserve migration, API, event, authorization, temporal, append-only, scientific, adapter-failure, and accessibility evidence. This TRD does not define a weaker duplicate threshold.
