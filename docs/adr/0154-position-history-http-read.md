# ADR 0154: Expose governed Position history through a read-only HTTP boundary

- **Status:** Proposed on active stacked PR #154; not protected-main truth until integrated
- **Date:** 2026-08-30
- **Owners:** Orgmetra People API / customer read boundary
- **Extends:** ADR 0008 (purpose-bound PII authorization), ADR 0152 (Position-history read), ADR 0153 (PostgreSQL Position-history read)

## Context

PR #152 defines the purpose-bound Position-history use case and PR #153 supplies
the canonical PostgreSQL read adapter, but neither exposes a customer-callable
transport route. Deployments need one stable boundary that preserves the same
tenant, purpose, field, bitemporal, and no-disclosure controls without adding
Person, Employment, Assignment, or employment-decision authority.

## Decision

Add `PositionHistoryAsgiApp` with this route:

```text
GET /v1/tenants/{tenant_record_id}/positions/{position_record_id}/history
    ?known_at=YYYY-MM-DDTHH:MM:SSZ
    &purpose=workforce_position_review
    &fields=effective_from,position_status_code
```

The boundary validates operational UUIDs, exact required query keys, ASCII
query syntax, a UTC RFC 3339 `known_at` ending in `Z`, lower snake-case purpose
and fields, and duplicate-field/parameter rejection before authentication. It
reuses the existing People ASGI JSON transport and authorization-header parser,
authenticates exactly one Bearer credential, then delegates to
`read_position_history()`. The operation declares
`orgmetra.people.position_history.read`, returns only authorized fields, uses
`Cache-Control: no-store` and `Vary: Authorization`, and maps malformed input,
authentication, authorization, integrity, and unexpected failures to the
published client-safe error envelope.

OpenAPI publishes the route, query/path parameters, `PositionHistoryView`, and
400/401/403/409/500 responses. The dedicated workflow checks the exact PR head,
compiles the service, and runs the complete People suite at 100% statement and
branch coverage.

## Consequences

- Customers receive one stable, read-only Position-history boundary.
- Existing Position-history service and PostgreSQL ownership boundaries remain
  the only owners of authorization, bitemporal validation, and persistence.
- Error support references are opaque and safe for customer correlation; the
  route does not expose backend exception details.
- The route intentionally does not add pagination, writes, cross-service joins,
  or high-impact employment decisions; those require separate contracts.

## Verification

The test-only child head `86cc40b1` fails during collection while the HTTP
adapter module is absent. The implementation must retain that test-first chain,
show exact-current-head hosted evidence, and remain a Draft stacked PR until
independent review and all protected central gates are authoritative.

RFC 3339, OpenAPI 3.2.0, NIST SP 800-53 Rev. 5, and PostgreSQL RLS/read-only
transaction guidance inform the boundary. They are defense-in-depth references,
not certification or merge evidence.
