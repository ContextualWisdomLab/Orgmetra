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
purpose authorization or persistence. The route delegates to a synchronous
Employment-history service/PostgreSQL adapter, so blocking connection/cursor/fetch
work must not execute on the ASGI event-loop thread.

## Decision

Add `EmploymentHistoryAsgiApp` with this route:

```text
GET /v1/tenants/{tenant_record_id}/people/{person_record_id}/employment-history
    ?known_at=YYYY-MM-DDTHH:MM:SSZ
    &purpose=employee_profile_review
    &fields=effective_from,employment_status_code
```

The boundary validates operational UUIDs, exact required query keys, ASCII query
syntax, a UTC RFC 3339 `known_at` ending in `Z`, lower snake-case purpose/fields,
and duplicate-field/parameter rejection before authentication. It caps the path
at 256 characters before route tokenization and the raw query at 4096 bytes before
`parse_qsl`; parser field count is bounded too. Path and raw-query values must be
exact built-in `str` and `bytes`, not subclasses: caller-defined subtypes can
override `__len__`, `strip`, or `decode`, so accepting them would execute mutable
Python behavior before authentication. Non-exact scalars fail closed before those
operations while preserving the existing 404 path and 400 query response classes.

Authentication accepts only exact `AuthenticatedPrincipal`. The route deliberately
reuses the canonical People `_send_json` contract inherited through #149/#55.
That emitter accepts a pre-generated `support_reference`, fills `error_code` and
`next_action`, and preserves the same opaque reference in the customer response.
The Employment route therefore must pass its pre-logged reference into the shared
emitter rather than duplicate the emitter's enrichment logic.

`read_employment_history()` remains synchronous. The ASGI adapter runs the whole
service call with `asyncio.to_thread(...)`; authorization, persistence, bitemporal
validation, and exception types remain unchanged, while synchronous DB work no
longer monopolizes the event-loop thread. This is event-loop isolation, not p95
performance acceptance.

The operation declares `orgmetra.people.employment_history.read`, returns only
authorized fields, uses `Cache-Control: no-store` and `Vary: Authorization`, and
maps malformed input, authentication, authorization, integrity, and unexpected
persistence failures to the published client-safe error envelope.

Repository acceptance remains owned by consolidated Foundation CI after this stack
returns to a protected-`develop` pull-request boundary. The retired feature-local
workflow is not recreated.

## Consequences

- Customer Employment history remains a read-only purpose-bound boundary.
- Parent service/PostgreSQL owners retain authorization and persistence truth.
- Caller-controlled parsing is bounded before protected work, and executable
  path/query scalar subtypes are rejected before overridden behavior can run.
- One support reference correlates route logging and the response through the
  canonical shared emitter.
- Synchronous Employment/PostgreSQL work is worker-thread isolated from ASGI;
  exact-candidate k6/E2E latency evidence remains separate.
- No pagination, export, mutation, cross-service join, or high-impact decision is
  introduced.

## Verification

Historical test-first and transport-hardening lineage remains unchanged through
route-tokenization repair `99c3ec578a57c31f039cab70b6e3a90a4b85623a`.

Sibling #154 review identified event-loop blocking in the analogous Position route.
That availability finding is also valid here. Test-only
`d998cd684adee518b04ddc37cfad7c17ea151d8c` adds a regression requiring the
protected Employment read to execute off the event-loop thread; predecessor
`03030dbccba3b6044e2b4d8201203f309d4f40de` is RED for that contract. Causal
repair `3432b08b67f28cf5e665346494104ec15d523590` introduces
`asyncio.to_thread(...)`.

The sibling #154 `support_reference` signature finding does **not** transfer to
#155: this stack already inherits #55's `_send_json(..., support_reference=...)`.
The initial sibling-style repair in `3432b08...` duplicated response enrichment and
omitted the canonical `support_reference` argument, causing the shared emitter to
generate a second reference. Test-first `a38c0b2286aff93ec19a766bcd63927754648e7b`
requires the Employment route's ERROR log reference to equal the response
`support_reference`. Causal repair `15220135234107de82c481816f19749198c61012`
restores canonical emitter ownership and also passes the already-generated
reference through `_send_error`, preventing double-reference correlation drift.

Issue #321 then generalized a separately verified transport-integrity mechanism.
Employment-local test-first `a6862f7f37184265a4827cf40cfbec0faff8ed09`
adds trapping `str`/`bytes` subclasses and requires rejection before their
`__len__`, `strip`, or `decode` behavior or any authenticator/persistence call.
The predecessor accepts them through `isinstance(...)`; causal repair
`e1618605d64262f7aea6a7e53692ce0903a946a1` changes the Employment path/query
ingress to exact built-in type checks. Canonical People owner #55 has its own
independent #321 RED/repair; neither lane borrows the other's acceptance verdict.

No hosted RED/GREEN is claimed for these stacked heads because #155 targets #149,
not protected `develop`. Final acceptance must be reacquired after the owner stack
returns to the protected lane, including Foundation, security, SAST, CodeQL,
model-backed review, qualifying independent review, and applicable latency evidence.

RFC 3339, OpenAPI 3.2.0, NIST zero-trust authorization guidance, and PostgreSQL
read-boundary guidance remain defense-in-depth references, not merge evidence.
