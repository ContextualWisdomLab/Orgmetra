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
opaque client-safe responses without exposing credential or backend details. The
ASGI boundary must also avoid running the synchronous Position-history service and
PostgreSQL adapter on the event-loop thread; a blocking connection/cursor/fetch path
would otherwise stall unrelated concurrent requests. Unexpected protected-read
failures must remain non-disclosing to the caller while still leaving enough
non-secret server evidence to correlate the opaque 500 response to the failed
backend boundary.

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

Unexpected identity-backend exceptions are translated to the same published
`ErrorResponse` shape used by the rest of the route. The opaque support reference
is generated once, logged with non-secret metadata, and returned in the payload;
`error`, `error_code`, `message`, `next_action`, and `support_reference` are all
present. The active Position-stack shared JSON emitter is a passthrough and only
receives arguments in its exact current signature. A compatibility regression
keeps route-log and response references equal so a later protected-truth adoption
of an evolved shared emitter cannot silently change that contract.

Unexpected persistence/protected-read exceptions use a separate Position-history
ERROR record containing only route, tenant identifier, exception type, and the
same opaque support reference returned to the caller. Exception messages, SQL,
credentials, bearer tokens, and backend payloads are not logged by this boundary.
This preserves client non-disclosure while giving operators a stable correlation
key and failure class. Authorization and integrity failures retain their 403 and
409 mappings rather than being reclassified as backend failures.

`read_position_history()` remains a synchronous domain/application contract because
its PostgreSQL port is synchronous. The ASGI adapter therefore executes the whole
service call through `asyncio.to_thread(...)`. Authorization, persistence, row
validation, and exception semantics stay unchanged, while blocking connection,
cursor, execute, and fetch work no longer runs on the event-loop thread. Exceptions
raised in the worker propagate through the await and are mapped by the existing
403/409/500 handlers. This is an event-loop isolation repair, not a claim that the
buyer-path p95 target has been measured or met.

The operation declares `orgmetra.people.position_history.read`, returns only
authorized fields, uses `Cache-Control: no-store` and `Vary: Authorization`, and
maps malformed input, authentication, authorization, integrity, and unexpected
failures to the published client-safe error envelope.

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
- Identity and persistence backend 500 responses remain schema-valid and correlate
  to the exact non-secret support reference recorded by the server.
- Synchronous Position-history/PostgreSQL work is isolated from the ASGI event
  loop; this does not replace later k6/E2E latency and capacity measurement.
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

Review then exposed the backend-envelope and event-loop defects. Test-only head
`88e28cbc565f49992e6de741d356582d20252c30` strengthened the identity-backend
failure contract and required the synchronous read port to execute off the ASGI
event-loop thread. Causal repair `17adbbf4044a0288489153f72e08179b78b54fd0`
returned the generated reference in the schema-valid payload and offloaded the
service call with `asyncio.to_thread(...)`.

A subsequent sibling-stack comparison incorrectly assumed that #154 already
inherited the newer People `_send_json(..., support_reference=...)` contract.
CodeRabbit revalidation showed the exact #154 tree still uses the Position-stack
passthrough emitter. Ordinary-forward `66b64fd550230bc20d884919cba1e045bb130c5c`
restored that exact signature rather than source-copying a mutable sibling owner.
`f1e303dc5fa947f9f6b404a609aba313fdce4f6e` is retained only as a future
compatibility guard and is not claimed as a RED against the current predecessor.

Test-only `d6d8e6469f80793d6a13060abb2a38de256a4b23` then added the persistence
observability contract: an unexpected protected-read failure must emit one
non-secret ERROR record whose support reference equals the opaque 500 response.
The predecessor only called generic `_send_error(...)`, losing the backend
exception class at server side. Causal repair
`411ba41631a2f31fa80aaadcb3f15d22aa8c26fe` adds the dedicated persistence
backend error path. Traceability is current through `ae03931ef7858eafaa3c8c0e626d1b392af9a7ea`.

These stacked heads have no protected-base PR-triggered Foundation run because the
PR targets #153 rather than `develop`; no hosted RED or GREEN is inferred from that
absence. No predecessor or feature-local GREEN is accepted as current-head evidence.
After the #152/#153 owner lineage reaches protected `develop`, the final exact #154
head must reacquire Foundation, security, SAST, CodeQL, model-backed review,
qualifying independent review, and applicable buyer-path latency evidence.

RFC 3339, OpenAPI 3.2.0, NIST SP 800-53 Rev. 5, and PostgreSQL RLS/read-only
transaction guidance inform the boundary. They are defense-in-depth references,
not certification or merge evidence.
