# UML

## Component diagram

```mermaid
flowchart LR
    ui[Role Workspaces] -->|OpenAPI commands and queries| gateway[Orgmetra Gateway]
    gateway --> people[people_core]
    gateway --> organization[organization_core]
    gateway --> jobs[job_architecture]
    gateway --> talent[talent_acquisition]
    gateway --> performance[performance_management]
    gateway --> validation[workforce_validation]
    gateway --> documents[document_records]
    gateway --> audit[audit_provenance]
    gateway --> integration[integration_hub]

    subgraph postgres[Shared physical PostgreSQL cluster]
        people_store[(people_core-owned schema)]
        organization_store[(organization_core-owned schema)]
        jobs_store[(job_architecture-owned schema)]
        talent_store[(talent_acquisition-owned schema)]
        performance_store[(performance_management-owned schema)]
        validation_store[(workforce_validation-owned schema)]
        documents_store[(document_records-owned schema)]
        audit_store[(audit_provenance-owned schema)]
        integration_store[(integration_hub-owned schema)]
    end

    people --> people_store
    organization --> organization_store
    jobs --> jobs_store
    talent --> talent_store
    performance --> performance_store
    validation --> validation_store
    documents --> documents_store
    audit --> audit_store
    integration --> integration_store

    people -. OpenAPI or versioned event .-> organization
    jobs -. OpenAPI or versioned event .-> talent
    talent -. versioned event .-> performance
    validation -. versioned event .-> audit
    integration -. versioned adapters .-> external[CWL Services]
```

The cluster is physically shared in the initial modular deployment. Each bounded context has a separate schema and role; direct reads of another context's application tables are prohibited.

## Selection decision sequence

```mermaid
sequenceDiagram
    actor Recruiter
    participant Gateway
    participant JobArchitecture
    participant TalentAcquisition
    participant WorkforceValidation
    participant Psychometrics
    participant Audit

    Recruiter->>Gateway: Request review(actor, tenant, purpose)
    Gateway->>JobArchitecture: Fetch published job profile and evidence version
    Gateway->>TalentAcquisition: Fetch candidate evidence packet versions
    Gateway->>WorkforceValidation: Fetch immutable result snapshot and provenance
    WorkforceValidation->>Psychometrics: Fetch immutable result snapshot and provenance
    Psychometrics-->>WorkforceValidation: Versioned result and provenance
    WorkforceValidation-->>Gateway: Orgmetra validation snapshot reference
    Gateway-->>Recruiter: Preview target, consequence, reason, and evidence versions
    Recruiter->>Gateway: Confirm(single-use confirmation reference)
    Gateway->>TalentAcquisition: Record(actor, purpose, reason, confirmation, evidence versions, idempotency key)
    TalentAcquisition->>Audit: Append decision and policy provenance
    Audit-->>TalentAcquisition: Audit reference
    TalentAcquisition-->>Gateway: Recorded decision and audit reference
    Gateway-->>Recruiter: Recorded result
```

Only an authorized human can produce the confirmation. LLM and integration identities can draft evidence but cannot call the record transition with a human confirmation. Psychometric snapshots are fetched only through `workforce_validation`; the Gateway never bypasses that owning adapter boundary.

## Employment state model

```mermaid
stateDiagram-v2
    [*] --> Candidate
    Candidate --> Offered: human_confirmed_offer_created
    Offered --> Worker: human_confirmed_hire_accepted
    Worker --> Leave: leave_started
    Leave --> Worker: leave_ended
    Worker --> FormerWorker: governed_employment_separation [active PR #64]
    Leave --> FormerWorker: governed_employment_separation [active PR #64]
    note right of FormerWorker
        Rehire is planned under #302.
        No implemented transition is claimed here.
    end note
```

A second Employment that overlaps an exclusive period is rejected unless it is marked `concurrent`. The active #64 separation path ends one exact current-known Employment through bitemporal supersession; it does not rewrite the prior business fact in place. Rehire remains a downstream #302 contract and, when implemented, is expected to create a new `employment_record` for the existing Person after successful prior separation. Until that contract reaches protected truth, this UML deliberately shows no `FormerWorker -> Worker` or `FormerWorker -> RehireCandidate` production transition.

## Governed Employment-separation sequence

```mermaid
sequenceDiagram
    actor HROps
    participant Gateway
    participant PeopleCore
    participant EmploymentDB as People PostgreSQL
    participant AssignmentBoundary
    participant Audit

    HROps->>Gateway: Preview separation target, consequence, reason, evidence
    Gateway-->>HROps: Exact Employment/version + controlled reason + evidence versions
    HROps->>Gateway: Confirm(single-use confirmation, Idempotency-Key)
    Gateway->>PeopleCore: POST /v1/employment-separations
    PeopleCore->>PeopleCore: Bind tenant, actor, workforce_admin purpose and exact command digest
    PeopleCore->>EmploymentDB: separate exact expected Employment version
    EmploymentDB->>EmploymentDB: Lock idempotency key, then Employment aggregate
    EmploymentDB->>EmploymentDB: Re-read current version and Assignment-conflict truth after lock
    alt stale/future/conflicting Assignment truth
        EmploymentDB-->>PeopleCore: Fail closed; no durable separation side effect
        PeopleCore-->>Gateway: Governed conflict response
        Gateway-->>HROps: Coordinate current truth and retry intentionally
    else authoritative transition accepted
        EmploymentDB->>EmploymentDB: Close recorded interval; add optional continuation + terminal version
        EmploymentDB->>Audit: Persist employment_separated audit/outbox evidence in same transaction
        EmploymentDB->>EmploymentDB: Append employment_separation_record + idempotency result
        EmploymentDB-->>PeopleCore: First durable terminal result or exact-key replay
        PeopleCore-->>Gateway: Governed separation receipt
        Gateway-->>HROps: Recorded terminal Employment state
    end
```

The diagram shows transaction ownership rather than service-to-service SQL. `AssignmentBoundary` remains the owner of Assignment lifecycle; Employment separation never closes or rewrites Assignment rows. Migration 0017 makes Assignment INSERT and separation serialize on the same Employment anchor, with a fresh post-lock coverage read. The separation database function is capability-separated behind dedicated owner/executor roles; application callers do not receive direct People/audit/outbox DML as a substitute.

ADR 0015 remains Proposed. This sequence is active-PR truth on #64, not a protected/released capability, until canonical PostgreSQL execution under #311 and the remaining security/review gates pass.

## Hire-to-assignment sequence

```mermaid
sequenceDiagram
    actor HROps
    participant Gateway
    participant PeopleCore
    participant JobArchitecture
    participant Kernel
    participant Audit

    HROps->>Gateway: Create employment(actor, tenant, purpose, confirmation, evidence, idempotency key)
    Gateway->>PeopleCore: Replay matching key or validate exclusive-or-concurrent overlap
    PeopleCore->>Kernel: validate_person_employment_exclusivity
    Kernel-->>PeopleCore: Accept or next-action error
    PeopleCore->>Audit: Persist employment, audit/outbox, and idempotency binding
    PeopleCore-->>Gateway: employment_record Location
    HROps->>Gateway: Create position(actor, tenant, purpose, confirmation, evidence, idempotency key)
    Gateway->>JobArchitecture: Replay matching key or bind organization and job
    JobArchitecture->>Audit: Persist position, audit/outbox, and idempotency binding
    JobArchitecture-->>Gateway: position_record Location
    HROps->>Gateway: Create assignment(actor, tenant, purpose, confirmation, evidence, idempotency key)
    Gateway->>PeopleCore: Replay matching key or validate_assignment_write
    PeopleCore->>Kernel: employment, position, portfolio, and seat checks
    Kernel-->>PeopleCore: Accept or next-action error
    PeopleCore->>Audit: Persist assignment, audit/outbox, and idempotency binding
    PeopleCore-->>Gateway: assignment_record Location
    Gateway-->>HROps: Review the roster, then approve or correct
```
