# ADR-0005: Purpose-bound tenant isolation and transactional audit evidence

- Status: Proposed
- Date: 2026-08-15
- Owners: Orgmetra maintainers
- Supersedes: none

## Context

Orgmetra must keep personal data required for legitimate HR work usable without
broadcasting it to unrelated services or model traces. Application-only tenant
filters are insufficient because a missed predicate can expose another
customer's employee records. Audit records written after a business transaction
can also be lost independently of the mutation they explain.

## Decision

The PostgreSQL adapter will:

1. require an immutable `PurposeContext` created by an authenticated host;
2. bind `tenant_reference` with transaction-local `set_config` before access;
3. enforce tenant scope again with forced PostgreSQL row-level security;
4. include tenant identity in relationship constraints so cross-tenant foreign
   keys fail at the database boundary;
5. append non-content audit evidence in the same transaction as each mutation;
6. make audit, selection, criterion-observation, candidate-link and employment-
   transition facts append-only at the database boundary;
7. expose stable repository errors without returning raw SQL or credentials.

The adapter does not decide whether a purpose is lawful or sufficient. The host
owns authentication, policy evaluation, consent where applicable, and mapping
enterprise identities to opaque references.

## Alternatives considered

### Blanket masking

Rejected. Names and other PII are necessary for authorized HR operations, and
masking the system of record would make the product unusable. Purpose-bound
access, encryption, retention and audit provide a stronger operational control.

### Application filters only

Rejected. One omitted predicate creates a cross-tenant disclosure path.

### Asynchronous audit after commit

Rejected for authoritative write evidence. An outbox may later distribute the
committed event, but the durable audit fact must share the business transaction.

### One database per tenant

Deferred as a deployment option. It improves blast-radius isolation but does not
remove the need for purpose, audit and fail-closed repository contracts.

## Consequences

- Fresh pre-GA databases apply migration `0002_tenant_audit_boundary.sql`.
- Application roles must be `NOSUPERUSER NOBYPASSRLS`.
- Direct generic SQL access by the application is out of scope.
- The current migration is not yet an upgrade contract for populated databases.
- Container image digests and a supported PostgreSQL minor-version matrix remain
  release gates before GA.

## Failure and recovery

A missing tenant context returns no RLS-protected rows. Database integrity or
availability errors roll back both business and audit writes. Operators recover
from a database outage through normal retry/idempotency handling; they do not
relax RLS or mutate immutable audit history.

## Verification

- real PostgreSQL 17 and 18 integration jobs;
- cross-tenant invisibility;
- same-input idempotency and conflicting-input refusal;
- missing relationship rollback;
- append-only trigger rejection;
- exact 100% production statement and branch coverage;
- public docstring audit.

## Security and governance impact

This decision supports purpose limitation, segregation of duties and auditable
access expected in SOC 2 and CSAP-oriented control design. It is an engineering
readiness decision, not a certification claim.
