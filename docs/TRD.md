# Technical Requirements Document: Orgmetra

## 1. Technology baseline

- Monorepo with explicit service boundaries.
- PostgreSQL for the HRIS system of record, physically shareable only through service-owned schemas and database roles.
- PostgreSQL deployments must permit the `btree_gist` extension for temporal exclusion constraints and `pgcrypto` for database-owned SHA-256 evidence sealing; managed PostgreSQL offerings must be checked for both extensions before deployment.
- OpenAPI 3.2.0 for HTTP APIs.
- AsyncAPI/CloudEvents-style event envelopes for asynchronous integration.
- JSON Schema Draft 2020-12 for payload validation.
- TypeScript for web workspaces and gateway/BFF surfaces where appropriate.
- Rust for mathematical and psychometric production compute.

Material mathematical and psychometric kernels must use bounded CPU multithreading with a fixed worker pool and documented oversubscription controls. A GPU backend is required when profiling shows material buyer benefit or a product requirement names GPU execution. The GPU result must be compared with the CPU `f64` reference across deterministic fixtures, simulated true parameters, edge cases, and production-sized benchmarks. Each kernel publishes tolerances for objective value, estimates, gradients, uncertainty, convergence, and failure classification; skipped or unavailable GPU execution cannot be reported as parity success.

## 2. Core services

| Canonical service identifier | Responsibility |
|---|---|
| `people_core` | Person identity anchors, names, employment, governed Employment separation, assignments, compensation, candidate-worker linkage, and identity references. |
| `organization_core` | Organization units, reporting relations, legal entities, locations, and positions. |
| `job_architecture` | Job profiles, tasks, FJA, KSAO, qualification rules, evidence, and SME approvals. |
| `talent_acquisition` | Requisitions, candidates, versioned decision-evidence sets, interviews, confirmations, and selection decisions. |
| `performance_management` | Performance cycles, criterion blueprints, observations, and calibration sessions. |
| `workforce_validation` | Validity studies, exact decision/evidence/outcome linkage, subgroup diagnostics, drift monitoring, selection utility, and scientific adapters. |
| `document_records` | Document metadata, source evidence, and immutable artifact references. |
| `audit_provenance` | Immutable audit and provenance graph. |
| `integration_hub` | CWL adapters, inbox/outbox state, and external HRIS migration adapters. |

These identifiers are canonical across deployment names, ACLs, metrics, generated clients, schemas, and event ownership. Display labels may use title case but cannot create a second service identity.

## 3. API design

- Commands require idempotency keys.
- Mutating requests require authenticated actor, tenant, purpose, resource, and decision context.
- Read APIs enforce tenant and field-level authorization.
- High-impact commands require previewed and recorded reason, confirmation, and exact evidence versions.
- A finalized high-impact selection command binds one immutable evidence-set version and a database-computed SHA-256 digest over canonical sorted evidence membership; later evidence membership changes are rejected.
- High-impact decision APIs return evidence sufficiency and escalation status.
- Generated server validation must enforce the OpenAPI contract before domain handlers execute.
- `POST /v1/employment-separations` is a high-impact People command on active PR #64. It binds tenant, Person, Employment, exact expected Employment version, effective separation date, actor, `workforce_admin` purpose, human confirmation, evidence reference/version, controlled reason and idempotency key before persistence.
- `separation_reason_code` is an exact enum: `voluntary_resignation`, `retirement_transition`, `fixed_term_completion`, `position_elimination`, or `employer_initiated_separation`. A syntactically valid but unrecognized lower-`snake_case` value fails closed before mutation.
- Employment separation does not implement rehire. #302 remains planned downstream and cannot consume mutable #64 source as an external runtime dependency.

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

`actor_reference` is required and resolves only inside the authorized tenant. `provenance_reference` is also required and resolves to an immutable audit bundle containing actor, policy decision, confirmation, reason, command digest, sealed evidence-set digest and evidence versions. Consumers must verify both fields before treating a high-impact event as accountable.

Employment separation emits the corresponding CloudEvents-compatible `employment_separated` audit envelope from database-owned post-lock recorded time. The audit/outbox fact, `employment_separation_record`, terminal bitemporal state and People idempotency result are one transaction; downstream workflow, payroll, identity deprovisioning and notification behavior begins only after that transaction through owned contracts/events.

## 5. Data model rules

- Stable entity anchors do not contain mutable descriptive attributes.
- Every authoritative HRIS relation carries an internal `tenant_record_id`; tenant-qualified foreign keys reject cross-tenant relationships before application logic runs.
- Application roles use forced PostgreSQL row-level security. Missing tenant context returns no tenant rows; tenant context never replaces actor/purpose/resource authorization.
- Versioned HR facts keep effective time and system-recorded time separately.
- The database rejects reversed temporal intervals and contradictory overlapping effective/system coordinates for single-valued version families.
- Retroactive correction closes the old recorded interval and inserts a replacement; business-column rewrites of protected bitemporal facts are rejected.
- Model multiple assignments with allocation ratios rather than applying single-valued exclusion semantics to legitimate multiple membership.
- Exclusive employments for one person cannot overlap; a second overlapping job must be marked `concurrent`.
- Assignment days must land on an `active` or `open` position version, and visible allocations for one seat cannot exceed 1.0000.
- Model external organization roles as time-varying relations when one entity can be a customer, partner, competitor, or vendor in different contexts.
- Keep assessment results as external immutable snapshot references unless a later ADR transfers instrument lifecycle ownership.
- Candidate-worker links, selection decisions, evidence-set membership after finalization, governed Employment-separation provenance, and validation-study decision/evidence/outcome links are append-only.
- An open `decision_evidence_set` carries no caller-supplied digest. Selection finalization requires at least one member, computes the canonical SHA-256 digest inside PostgreSQL, and seals exactly one set in the same transaction; a sealed set cannot accept new members, be reused by a second decision, or point to a different consuming decision.
- Validity studies reference exact selection decisions, sealed evidence sets and criterion observations through normalized link relations so criterion-related validity can be reconstructed without copying specialist-system payloads.

### 5.1 Employment-separation invariant

The active #64 implementation follows ADR 0015 and remains active-PR, not protected/released, truth while that ADR is Proposed.

- A separation corrects one exact current-known `active` or `leave` `employment_record_version`; it never rewrites the prior protected business columns in place.
- The database takes one post-lock recorded timestamp, closes the expected version's recorded interval, creates an optional continuation version for the pre-separation effective interval, and creates one terminal `terminated` version beginning at the requested separation boundary.
- The continuation version's `effective_to` is structural interval closure. The terminal version plus `employment_separation_record` is the authoritative separation fact.
- `employment_separation_record` tenant-qualifies and binds the prior version, optional continuation version, terminal version, controlled reason, evidence, human confirmation, actor/purpose, recorded timestamp and immutable audit identity.
- The exact tenant+route+idempotency key serializes matching/reused command identity. Distinct separation commands serialize on the durable `employment_record` aggregate anchor.
- Assignment INSERT and separation use the same Employment anchor as their database conflict boundary. After waiting on that lock, Assignment coverage must be re-read in a separate statement so READ COMMITTED cannot continue from a pre-separation statement snapshot.
- Separation never creates, closes, rewrites or deletes Assignment-owned rows. An Assignment effective on or after the requested boundary blocks separation until its owning boundary coordinates it; historical Assignment ending at or before the boundary remains valid.
- The separation function uses a dedicated `NOLOGIN`/`NOBYPASSRLS` SECURITY DEFINER owner, while a distinct executor capability receives function `EXECUTE` without direct People/audit/outbox table DML. Ordinary Assignment writers do not receive broad Employment UPDATE privilege solely for locking.
- Same-key replay after an uncertain caller outcome must return the first durable terminal result without retry-only separation/audit/outbox side effects.

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

`docs/TEST_STRATEGY.md` is the canonical coverage and execution contract. Every service must satisfy its 100% statement/branch coverage requirement where the pinned toolchain exposes those metrics, document exact commands, and preserve migration, API, event, authorization, temporal, tenant-isolation, evidence-sealing, append-only, scientific, adapter-failure, and accessibility evidence. PostgreSQL contract tests use a `NOBYPASSRLS` application role and cover missing tenant context, cross-tenant references, concurrent bitemporal corrections, database-owned evidence digest computation, empty-evidence rejection, and post-decision evidence drift. This TRD does not define a weaker duplicate threshold.

Before ADR 0015 can move from Proposed, canonical PostgreSQL Foundation execution must cover the Employment-separation root plus its same-database concurrency/cleanup/recovery companions and the Assignment/separation serialization root. Acceptance includes bitemporal historical reconstruction, atomic audit/outbox/idempotency durability, exact-key replay, semantic-key conflicts, stale/future/cross-tenant hostile cases, real PostgreSQL blocker graphs for exact-key and distinct-key races, both Assignment-first and separation-first commit orders, failure-path server-session quiescence, uncertain-commit recovery, FORCE RLS, and capability separation. Elapsed time alone is not concurrency evidence.

The canonical execution owner is #311 after prerequisite Foundation integration. A GREEN legacy filename switchboard that does not execute the newly registered roots/companions is not evidence that these acceptance cases passed. Security/review gates remain independently required, and no protected release or latency SLO is implied by active-branch test success.
