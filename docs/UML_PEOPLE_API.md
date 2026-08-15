# People API UML views

## Component boundary

```mermaid
flowchart LR
    client["Authorized HR Client"] -->|"Bearer + bounded JSON"| api["Orgmetra People API"]
    api -->|"Validate token and purpose"| identity["Injected TokenAuthorizer"]
    api -->|"PurposeContext"| repository["PeopleRepository port"]
    repository -->|"Transaction-local tenant"| postgres["Orgmetra PostgreSQL"]
    postgres -->|"Forced RLS"| records["People and candidate records"]
    postgres -->|"Same transaction"| audit["Reference-only audit_event"]
    identity -.->|"Future adapter"| keyverse["Keyverse OIDC / SCIM"]
```

## Create-person sequence

```mermaid
sequenceDiagram
    participant Client
    participant Boundary as Request Boundary
    participant API as People API
    participant Auth as TokenAuthorizer
    participant Repo as PeopleRepository
    participant DB as PostgreSQL

    Client->>Boundary: POST /v1/people + Bearer + JSON
    Boundary->>Boundary: Enforce declared and actual byte limit
    Boundary->>API: Bounded request + generated trace reference
    API->>Auth: authorize(token, people_admin)
    Auth-->>API: tenant reference + actor reference + allowed purposes
    API->>API: Build immutable PurposeContext
    API->>Repo: create_person(context, payload)
    Repo->>DB: BEGIN + set_config tenant
    Repo->>DB: INSERT person_record
    Repo->>DB: INSERT audit_event
    DB-->>Repo: COMMIT both facts
    Repo-->>API: PersonSnapshot
    API-->>Client: 201 PersonResponse + X-Request-Id
```

## Failure sequence

```mermaid
sequenceDiagram
    participant Client
    participant API as People API
    participant Auth as TokenAuthorizer
    participant Repo as PeopleRepository
    participant DB as PostgreSQL

    Client->>API: Request
    API->>Auth: authorize required purpose
    alt Missing or invalid credential
        Auth-->>API: AuthenticationFailed
        API-->>Client: 401 problem detail
    else Purpose not granted
        Auth-->>API: Principal without purpose
        API-->>Client: 403 problem detail
    else Authorized
        API->>Repo: Purpose-bound operation
        Repo->>DB: Transaction
        alt Immutable identity conflict
            DB-->>Repo: Integrity failure
            Repo-->>API: RepositoryConflictError
            API-->>Client: 409 without existing data
        else Dependency unavailable
            DB-->>Repo: Connection failure
            Repo-->>API: RepositoryUnavailableError
            API-->>Client: 503 + Retry-After
        end
    end
```

The diagrams are design authority for this active PR only. They become protected-
main truth only after the full dependency stack merges with fresh checks and
review.
