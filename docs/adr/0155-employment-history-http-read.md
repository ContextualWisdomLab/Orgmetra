# ADR 0155: Expose governed Employment history through a read-only HTTP boundary

- **Status:** Proposed on active stacked PR #155; not protected-`develop` truth until integrated
- **Date:** 2026-08-30
- **Owners:** Orgmetra People API / customer read boundary
- **Extends:** ADR 0008 (purpose-bound PII authorization), ADR 0149 (Employment-history read)

## Context

PR #149 defines the purpose-bound Employment-history use case, but it does not
expose a customer-callable transport route. Deployments need one stable HTTP
boundary that preserves the same tenant, Person, purpose, field, bitemporal,
and no-disclosure controls without adding Employment mutation or employment-
decision authority.

The transport also sits directly on caller-controlled HTTP input and an external
identity backend. Those boundaries must remain bounded and fail closed before
purpose authorization or persistence: an oversized request must not consume
unbounded parser work, an unexpected authenticator failure must not escape the
ASGI boundary, and an arbitrary object returned by an authenticator must not be
treated as an authenticated Orgmetra principal.

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
caps the path at 256 characters **before route tokenization** and the raw query
string at 4096 bytes before query parsing. `parse_qsl` is additionally bounded to
one more than the exact required-key cardinality. The ordering is part of the
security contract: an oversized path cannot reach the route helper's
`strip()`/`split()` decomposition or UUID parsing. The route reuses the existing
People ASGI JSON transport and bounded authorization-header parser.

The route authenticates exactly one Bearer credential and accepts only an exact
`AuthenticatedPrincipal`. `AuthenticationFailed` maps to 401. Any other identity-
backend exception or noncanonical authenticator result is logged with an opaque
support reference and maps to the client-safe 500 envelope; the exception text
and bearer credential are not returned. Only after that identity boundary does
the route delegate to `read_employment_history()`.

The operation declares `orgmetra.people.employment_history.read`, returns only
authorized fields, uses `Cache-Control: no-store` and `Vary: Authorization`, and
maps malformed input, authentication, authorization, integrity, and unexpected
persistence failures to the published client-safe error envelope.

OpenAPI publishes the route, query/path parameters, Employment-history response,
scope, and 400/401/403/409 responses. Repository-owned acceptance is executed by
the canonical Foundation CI after this stacked lane returns to a protected-
`develop` pull-request boundary. The historical feature-local Employment-history
workflow is retired; its service tests remain part of the complete People suite
and retain the exact 100% statement and branch coverage requirement.

## Consequences

- Customers receive one stable, read-only Employment-history boundary.
- Existing Employment-history service ownership remains responsible for
  purpose-bound authorization, bitemporal validation, and persistence access.
- Caller-controlled route and query work is bounded before route/query parser or
  authentication work.
- Identity-backend failures and invalid principal objects cannot become uncaught
  ASGI failures or reach protected persistence.
- Error support references are opaque and safe for customer correlation; the
  route does not expose backend exception details.
- The route intentionally does not add pagination, export, writes,
  cross-service joins, or high-impact employment decisions; each requires a
  separate contract.
- Current #149 contains later application-integrity repairs and protected #161
  workflow consolidation. This PR adopted that parent through ordinary non-force
  reconciliation before the current transport hardening.

## Verification

The original test-only child head `6c2d6b89` failed during collection while the
HTTP adapter module was absent. That historical test-first chain is retained.

A transport-boundary review found that the Employment-history route had not
inherited four controls already present on the canonical People HTTP path:
bounded path length, bounded query bytes/field parsing, exact principal type,
and client-safe handling of unexpected identity-backend failure. Test-first
commit `2bcf5586745b57b19b65a9b9c801497a409c3b66` added focused regressions and
repair `15cd1ec7680dd059fa926bad88d7a89c0598716f` implemented those boundaries.

A later exact-order review found that the 256-character path check still occurred
after `_looks_like_employment_history_route()`, so oversized input reached
`strip()`/`split()` before rejection. Test-only head
`8a367eb8885807dc21581c55e6a21b10e2ca5799` patches that route helper to fail
if called for an oversized path; it is RED against the preceding order. Causal
repair `99c3ec578a57c31f039cab70b6e3a90a4b85623a` moves the length gate ahead of
route tokenization while retaining the existing 404 behavior for non-string and
normal-sized nonmatching routes.

Because #155 remains intentionally stacked on #149, the protected Foundation
pull-request trigger does not provide hosted RED or GREEN evidence for these
stacked heads. After the owner stack reaches protected `develop`, the final exact
head must reacquire Foundation, security, SAST, CodeQL, model-review, and
qualifying independent-review evidence. Historical and predecessor-head results
do not transfer.

RFC 3339, OpenAPI 3.2.0, NIST zero-trust authorization guidance, and
PostgreSQL temporal/read-boundary guidance inform this transport decision. They
are defense-in-depth references, not certification or merge evidence.
