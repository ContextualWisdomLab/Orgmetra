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

The HTTP boundary also receives attacker-controlled path/query bytes and delegates
authentication to the Keyverse-facing identity boundary. It must bound parser work
before authentication, reject a noncanonical authenticated-principal object before
the governed service is called, and turn unexpected identity-backend failures into
opaque client-safe responses without exposing credential or backend details.

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
and fields, and duplicate-field/parameter rejection before authentication. Path
input is capped at 256 characters **before route tokenization**, and raw query
input is capped at 4096 bytes before `parse_qsl`; `parse_qsl` also receives a
bounded field count. The ordering is part of the security contract: an oversized
path must not reach `strip()`/`split()` route decomposition or UUID parsing. The
boundary reuses the existing People ASGI JSON transport and authorization-header
parser, authenticates exactly one Bearer credential, requires the exact
`AuthenticatedPrincipal` runtime type, then delegates to `read_position_history()`.
Unexpected identity-backend exceptions are translated to an opaque 500 response
before the service or persistence boundary is entered. The operation declares
`orgmetra.people.position_history.read`, returns only authorized fields, uses
`Cache-Control: no-store` and `Vary: Authorization`, and maps malformed input,
authentication, authorization, integrity, and unexpected failures to the published
client-safe error envelope.

OpenAPI publishes the route, query/path parameters, `PositionHistoryView`, and
400/401/403/409/500 responses. Repository acceptance is owned by consolidated
Foundation CI; the historical feature-local workflow is retired and its results
must not be treated as evidence for a later exact head.

## Consequences

- Customers receive one stable, read-only Position-history boundary.
- Existing Position-history service and PostgreSQL ownership boundaries remain
  the only owners of authorization, bitemporal validation, and persistence.
- Oversized transport input is rejected before route/query parser work or
  authentication, and an invalid principal or failed identity backend cannot
  reach protected persistence.
- Error support references are opaque and safe for customer correlation; the
  route does not expose backend exception details.
- The route intentionally does not add pagination, writes, cross-service joins,
  or high-impact employment decisions; those require separate contracts.

## Verification

The historical contract-only child head `86cc40b1` failed during collection while
the HTTP adapter module was absent. The original hardening chain added focused
regressions proving oversized paths never reach UUID parsing, oversized query
strings never reach `parse_qsl`, unexpected identity-backend exceptions return a
non-disclosing 500 without persistence, and noncanonical principal objects are
rejected before `read_position_history()`.

After semantic restack, test-only head `7ae776750b20f621468a5f188f5dbb0130bf1d97`
strengthened the path bound to require rejection before the route tokenizer itself.
The preceding implementation still called `_looks_like_position_history_route()`
before checking length, so that regression is a real RED against the prior order.
Causal repair `5d239e7db8a0ddb72a367c83e8b285f87421753c`
moves the length gate ahead of route decomposition while preserving the existing
404 behavior for non-string and nonmatching normal-sized paths.

No predecessor or feature-local GREEN is accepted as current-head evidence. After
the #152/#153 owner lineage reaches the protected `develop` lane, the final exact
#154 head must reacquire Foundation, security, SAST, CodeQL, model-backed review,
and qualifying independent review evidence.

RFC 3339, OpenAPI 3.2.0, NIST SP 800-53 Rev. 5, and PostgreSQL RLS/read-only
transaction guidance inform the boundary. They are defense-in-depth references,
not certification or merge evidence.
