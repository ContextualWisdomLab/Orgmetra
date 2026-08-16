# Orgmetra Foundation Design

Date: 2026-08-15  
Status: Accepted for implementation

## Problem

Build the minimum executable foundation for an evidence-centered HRIS/HCM without prematurely implementing the entire product or creating a distributed monolith. The foundation must prove the hardest domain invariants early: separate person/employment/job/position/assignment concepts, bitemporal history, explicit candidate-worker continuity, purpose-bound authorization contracts, and optional CWL integrations.

## Approaches considered

### 1. Full microservices from day one

Rejected. It creates deployment, network, contract, and observability complexity before domain boundaries and product workflows are proven.

### 2. Conventional HR CRUD monolith

Rejected. It encourages one mutable employee model, implicit cross-domain joins, and later extraction pain.

### 3. Modular monorepo with bounded deployable units

Accepted. Domain packages and persistence ownership are strict from the start; initial services may be co-deployed, and independently measurable needs trigger extraction.

## Foundation scope

### Repository/tooling

- pnpm/Turborepo TypeScript workspace.
- Cargo workspace reserved for Rust computation.
- `just`-style top-level commands.
- Strict formatting, type checking, tests, coverage, docstrings, dependency boundaries, security, and documentation gates.

### First executable vertical slice

```text
Create person
-> create employment
-> create organization unit and job
-> create position
-> assign person to position
-> correct effective-dated assignment
-> query effective-as-of and known-at history
-> emit/audit versioned events
```

This slice has no dependency on optional CWL services.

### Initial deployment units

- `core-hris-service`: people, employment, organization, job, position, assignment.
- `audit-provenance-service`: authoritative audit and event evidence; may begin as an owned module deployed together with core.
- `orgmetra-gateway`: HTTP/auth context boundary.
- `employee-workspace` and `hr-workspace`: thin clients after API foundation.

### First adapter

Keyverse OIDC/SCIM contract is the first external adapter because identity and deprovisioning are foundational. It remains optional in local tests through a synthetic identity adapter.

## Domain design

### Aggregates

- `PersonRecord`
- `EmploymentRecord`
- `OrganizationUnit`
- `JobProfile` / immutable `JobProfileVersion`
- `PositionRecord`
- `AssignmentRecord`

Each aggregate has a stable ID. Effective-dated facts have immutable recorded versions.

### Temporal value objects

```text
EffectivePeriod
RecordedPeriod
TemporalQuery
RecordRevision
```

Intervals use inclusive lower and exclusive upper bounds. System-recorded time is assigned by the service clock and not caller-controlled.

### Commands

```text
CreatePersonRecord
CreateEmploymentRecord
CreateOrganizationUnit
CreateJobProfile
PublishJobProfileVersion
CreatePositionRecord
CreateAssignmentRecord
CorrectAssignmentRecord
```

Commands contain tenant, actor, purpose, idempotency, expected revision, evidence, and correlation context.

### Queries

```text
GetCurrentPersonRecord
GetAssignmentAtEffectiveTime
GetAssignmentAsKnownAt
GetAssignmentHistory
ListCurrentAssignments
```

## Persistence design

PostgreSQL stores stable aggregate tables and immutable version tables. Version rows include effective and recorded ranges. Non-overlap constraints protect exclusive periods. Service transactions write domain state, audit metadata, and outbox record atomically.

Initial migration contains only the first vertical-slice entities. Later job-analysis/candidate/performance tables are not created prematurely.

## Authorization design

A transport-independent authorization interface receives:

```text
actor
tenant
purpose
action
resource metadata
field classification
relationship context
current/effective time
```

The first implementation supplies a deterministic policy adapter and tests. Keyverse provides authenticated subject/claims only; domain authorization remains inside Orgmetra.

## Event design

CloudEvents-compatible events are serialized from typed domain events. Payload contains opaque references and minimum non-sensitive state. Transactional outbox and inbox deduplication are introduced before external event delivery.

## Error handling

Domain errors are typed and mapped to stable Problem Details codes with safe next actions:

- invalid effective period;
- exclusive overlap;
- allocation conflict;
- stale revision;
- person/employment/position not found within authorized tenant;
- purpose/action denied;
- idempotency conflict;
- unsupported transition.

No raw SQL, stack, secret, or sensitive input is exposed.

## Testing

TDD sequence:

1. RED domain invariants.
2. Pure domain implementation.
3. RED PostgreSQL integration.
4. Migrations/repositories/transactions.
5. RED API contract.
6. HTTP adapter.
7. Browser workflow after API stabilizes.

Realistic scenarios include concurrent assignments, allocation conflict, retroactive correction, rehire, cross-tenant ID, stale edit, outbox crash/replay, backup/restore, and historical as-known query.

Coverage and documentation gates are exact 100% for owned production code.

## Security

- Synthetic fixtures only.
- Purpose-bound field delivery.
- Tenant derived from trusted auth context.
- Parameterized SQL and bounded API inputs.
- No unrestricted document/model functionality in the first slice.
- Keyverse adapter has explicit issuer/audience/SCIM capability contract.
- Logs/events contain opaque references only.

## UI baseline

The Figma baseline supplies HR Home and Employee Profile temporal views. UI implementation begins only after the API/domain vertical slice is executable. Storybook foundations precede page composition.

## Exit criteria

- Monorepo builds from a clean checkout.
- First vertical slice passes domain, PostgreSQL, API, concurrency, authorization, event, migration, and restore tests.
- Production statement/branch coverage and public API docs are 100%.
- Required security/supply-chain/docs checks pass.
- Architecture/ADR/API/ERD/traceability match shipped code.
- No optional CWL dependency is required for core readiness.
