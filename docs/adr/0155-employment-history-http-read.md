# ADR 0155: Expose governed Employment history through a read-only HTTP boundary

- **Status:** Proposed on active stacked PR #155; not protected-main truth until integrated
- **Date:** 2026-08-30
- **Owners:** Orgmetra People API / customer read boundary
- **Extends:** ADR 0008 (purpose-bound PII authorization), ADR 0149 (Employment-history read)

## Context

PR #149 defines the purpose-bound Employment-history use case, but it does not
expose a customer-callable transport route. Deployments need one stable HTTP
boundary that preserves the same tenant, Person, purpose, field, bitemporal,
and no-disclosure controls without adding Employment mutation or employment-
decision authority.

## Decision

Add `EmploymentHistoryAsgiApp` with this route:

```text
GET /v1/tenants/{tenant_record_id}/people/{person_record_id}/employment-history
    ?known_at=YYYY-MM-DDTHH:MM:SSZ
    &purpose=employee_profile_review
    &fields=effective_from,employment_status_code
```

The boundary validates operational UUIDs, exact required query keys, ASCII
query syntax, a UTC RFC 3339 `known_at` ending in `Z`, lower snake-case purpose
and fields, and duplicate-field/parameter rejection before authentication. It
reuses the existing People ASGI JSON transport and authorization-header parser,
authenticates exactly one Bearer credential, then delegates to
`read_employment_history()`. The operation declares
`orgmetra.people.employment_history.read`, returns only authorized fields, uses
`Cache-Control: no-store` and `Vary: Authorization`, and maps malformed input,
authentication, authorization, integrity, and unexpected failures to the
published client-safe error envelope.

OpenAPI publishes the route, query/path parameters, Employment-history response,
scope, and 400/401/403/409 responses. The dedicated workflow checks the exact
PR head, compiles the service, and runs the complete People suite at 100%
statement and branch coverage.

## Consequences

- Customers receive one stable, read-only Employment-history boundary.
- Existing Employment-history service ownership remains responsible for
  purpose-bound authorization, bitemporal validation, and persistence access.
- Error support references are opaque and safe for customer correlation; the
  route does not expose backend exception details.
- The route intentionally does not add pagination, export, writes,
  cross-service joins, or high-impact employment decisions; each requires a
  separate contract.

## Verification

The test-only child head `6c2d6b89` fails during collection while the HTTP
adapter module is absent. The implementation retains that test-first chain and
must remain a Draft stacked PR until independent review and all protected
central gates are authoritative.

RFC 3339, OpenAPI 3.2.0, NIST zero-trust authorization guidance, and
PostgreSQL temporal/read-boundary guidance inform this transport decision. They
are defense-in-depth references, not certification or merge evidence.
