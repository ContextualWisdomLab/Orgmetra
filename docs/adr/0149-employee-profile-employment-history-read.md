# ADR 0149: Purpose-bound employee Employment-history read

- **Status:** Proposed on active PR #149; becomes Accepted only after normal protected integration.
- **Date:** 2026-08-29
- **Owners:** Orgmetra People API / HRIS core
- **Extends:** ADR 0003 (bitemporal HRIS data), ADR 0008 (purpose-bound PII authorization)

## Decision

The employee profile reads Employment history through a read-only People API service boundary that authorizes the exact tenant, Person, purpose, operation, and requested field set **before** calling the injected persistence port. The persistence adapter remains a separate port; this slice does not create a second Employment source of truth and does not introduce cross-service application-table SQL.

Each persistence row carries a durable Employment identity, a durable Employment-version identity, controlled Employment status and concurrency codes, business-effective (`effective_from`, `effective_to`) coordinates, and system-recorded (`recorded_from`, `recorded_to`) coordinates. `known_at` selects the half-open recorded interval `[recorded_from, recorded_to)`. Trust-bearing system instants require an exact built-in `datetime` using Python's built-in fixed-offset `timezone` at zero offset so validation and canonical rendering cannot depend on mutable caller-defined timezone behavior.

Python's exact `UUID` object is not treated as immutable storage merely because it is normally used as a value object: low-level `object.__setattr__` can rewrite its internal `int` attribute. `EmploymentHistoryRecord` therefore validates each incoming UUID once, requires an exact built-in integer in Orgmetra's operational range, stores only that integer scalar in tuple-backed state, and returns a fresh UUID view when callers request the public identity. The request tenant and Person identifiers are detached to the same immutable scalar form before authorization or the untrusted persistence call. This prevents caller-held, persistence-held, or response-exposed UUID aliases from rewriting an already validated identity.

Persistence output remains untrusted. Exact tuple and row types are only shape checks, so the service reconstructs every accepted `EmploymentHistoryRecord` through the public validating constructor before tenant/Person scope, system-time visibility, version uniqueness, business-time overlap checks, deterministic sorting, or authorized field emission. That reconstruction remains necessary because low-level tuple construction can bypass the public validating constructor; forged or malformed exact-type rows therefore fail closed at runtime integrity validation rather than becoming authorized output.

Structural in-process immutability is not a substitute for a transactional database snapshot, MVCC, row/version locking, or the persistence adapter's own consistency guarantees. A future database adapter remains responsible for returning one transactionally coherent bitemporal view at the requested knowledge cutoff.

Only policy-authorized fields are emitted. Employment identity and version identity are not unconditional response-envelope fields; a caller authorized only for status receives status only. This preserves field minimization and prevents identifiers from becoming a side channel around purpose-bound authorization.

## Security and privacy consequences

Authorization is resource-centric and per request. NIST SP 800-207 and SP 800-207A support resource/service authorization decisions independent of network location; Orgmetra applies that principle through the existing Keyverse adapter contract rather than embedding another policy engine.

The persistence-alias boundary is treated as a local integrity concern rather than as evidence that the persistence adapter is malicious. Immutable scalar identity storage closes both top-level row rewriting and nested UUID alias rewriting. Service-owned reconstruction preserves fail-closed validation even for deliberately forged low-level tuple instances. This does not add cross-service locks or weaken field minimization.

The read boundary does not infer attendance, availability, fitness, compensation, performance, candidate status, or employment-decision authority. It exposes only authoritative Employment facts already permitted by policy for the requested Person and system-time cutoff.

## Data consequences

This ADR preserves the normalized distinction among Person, Employment, Organization, Job, Position, and Assignment. It changes no database schema. A future PostgreSQL adapter must remain tenant-scoped and RLS-governed and must read only Orgmetra-owned Employment tables through the People service boundary.

## Verification

PR #149 must demonstrate authorization-before-retrieval, tenant/Person isolation, half-open system-time visibility, controlled codes, exact UUID/time validation, immutable scalar detachment of trust-bearing UUID identities, field minimization, schema/type drift failure, structural resistance to retained-alias rewriting, fail-closed revalidation of low-level forged exact-type rows, duplicate-version rejection, business-time overlap rejection, deterministic ordering, exact 100% owned People API statement/branch coverage, and all applicable repository/security/central gates before integration.
