# ARCHITECTURE.md

## Architecture thesis

Orgmetra is a monorepo-hosted, modular, MSA-ready HRIS/HCM platform. It owns employment truth and integrates CWL specialist systems through explicit, versioned contracts.

```mermaid
flowchart LR
    employee[Employee Workspace] --> gateway[Orgmetra Gateway]
    manager[Manager Workspace] --> gateway
    recruiter[Recruiter Workspace] --> gateway
    hr[HR Workspace] --> gateway
    analyst[Analyst Workspace] --> gateway
    admin[Admin Console] --> gateway

    gateway --> people[people_core]
    gateway --> organization[organization_core]
    gateway --> jobs[job_architecture]
    gateway --> talent[talent_acquisition]
    gateway --> performance[performance_management]
    gateway --> validation[workforce_validation]
    gateway --> documents[document_records]
    gateway --> integration[integration_hub]
    gateway --> audit[audit_provenance]

    subgraph postgres[Shared physical Orgmetra PostgreSQL cluster]
        people_schema[(people_core schema)]
        organization_schema[(organization_core schema)]
        jobs_schema[(job_architecture schema)]
        talent_schema[(talent_acquisition schema)]
        performance_schema[(performance_management schema)]
        validation_schema[(workforce_validation schema)]
        documents_schema[(document_records schema)]
        integration_schema[(integration_hub schema)]
        audit_schema[(audit_provenance schema)]
    end

    people --> people_schema
    organization --> organization_schema
    jobs --> jobs_schema
    talent --> talent_schema
    performance --> performance_schema
    validation --> validation_schema
    documents --> documents_schema
    integration --> integration_schema
    audit --> audit_schema

    validation --> evidence[(Evidence object store)]
    documents --> evidence

    integration -. versioned adapter .-> keyverse[Keyverse]
    integration -. versioned adapter .-> naruon[Naruon]
    validation -. snapshot contract .-> psych[Psychometrics Commons]
    validation -. temporal analysis contract .-> tepp[TEPP]
    jobs -. ontology contract .-> semantic[Semantic Data Portal]
    jobs -. draft-only workflow .-> orchestrator[Contextual Orchestrator]
    documents -. artifact adapter .-> doc_services[Clearfolio and NewsDOM]
    integration -. migration adapter .-> migration[MHTML ETL Gateway and mightyETL]
```

The diagram shows one physical PostgreSQL cluster for the initial modular deployment, not a shared application schema. Each bounded context owns a separate schema, database role, migration history, and generated data-access layer.

## Runtime layers

1. **Role workspaces**: employee, manager, recruiter, HR, analyst, and admin.
2. **Orgmetra Gateway**: API aggregation, tenant context, purpose-bound authorization, idempotency, and event-envelope handling.
3. **Domain services**: `people_core`, `organization_core`, `job_architecture`, `talent_acquisition`, `performance_management`, `workforce_validation`, `document_records`, `integration_hub`, and `audit_provenance`.
4. **Stores**: service-owned PostgreSQL schemas, evidence object store, audit/provenance store, and search/vector store.
5. **External CWL services**: Keyverse, Naruon, Psychometrics Commons, TEPP, Semantic Data Portal, Contextual Orchestrator, Clearfolio, NewsDOM, MHTML ETL Gateway, and mightyETL.

## Database ownership and access

The initial deployment may share one physical PostgreSQL cluster. Logical isolation is mandatory:

| Service identifier | Owned schema and representative tables | Database role |
|---|---|---|
| `people_core` | `people_core`: person, name, employment, assignment, compensation, and candidate-worker linkage records | `people_core_role` |
| `organization_core` | `organization_core`: organization units and position records | `organization_core_role` |
| `job_architecture` | `job_architecture`: job profiles and publication evidence | `job_architecture_role` |
| `talent_acquisition` | `talent_acquisition`: candidate profiles, selection decisions, and decision evidence | `talent_acquisition_role` |
| `performance_management` | `performance_management`: criterion blueprints and observations | `performance_management_role` |
| `workforce_validation` | `workforce_validation`: validity-study registry and external result references | `workforce_validation_role` |
| `document_records` | `document_records`: document metadata and immutable artifact references | `document_records_role` |
| `integration_hub` | `integration_hub`: idempotency, inbox/outbox, and adapter state | `integration_hub_role` |
| `audit_provenance` | `audit_provenance`: append-only audit and provenance records | `audit_provenance_role` |

A service role may read and write only its owned application tables. Cross-service foreign identifiers are opaque references or explicitly approved database constraints inside the modular deployment. A service must never query another service's application tables directly. Cross-boundary reads and commands use generated OpenAPI clients; asynchronous propagation uses versioned AsyncAPI/CloudEvents contracts. Extraction into separate databases must not change those contracts.

## Data ownership

Orgmetra is authoritative for employment facts. It stores foreign references to external artifacts but not external service internals. External products can provide evidence and computation but do not own employment truth.

## Service extraction strategy

The foundation starts as a monorepo with separately deployable services. Each service owns its schema, migration path, database role, API, events, telemetry namespace, and release identity. Physical co-location is an implementation choice, not permission to bypass service boundaries.

## Security posture

Access is tenant-, actor-, purpose-, resource-, and lifetime-scoped. High-impact decisions require preview, explicit human confirmation, versioned evidence, immutable decision records, and attributable audit events. LLM outputs are draft evidence only.
