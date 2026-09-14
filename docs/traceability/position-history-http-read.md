# Position-history HTTP read traceability

**Lifecycle status:** Active stacked PR #154 only. This document does not claim protected-`develop` integration.

## Buyer problem

PR #152 defines an authorized Position-history read and PR #153 connects it to
canonical PostgreSQL truth. A customer still needs one stable HTTP boundary to
request that history without deployment-specific parsing, authentication, or
serialization code widening the data surface.

## Requirement-to-evidence matrix

| Requirement | Production boundary | Regression |
| --- | --- | --- |
| Reject executable outer ASGI scope authority | `PositionHistoryAsgiApp` requires an exact built-in `dict` before any scope field access; scope type/method are compared only after exact built-in `str` checks | trapping `dict` and `str` subclasses prove `.get()`, item access, and comparison overrides cannot execute before rejection; authentication and persistence remain untouched |
| Bound untrusted transport input before protected work | `PositionHistoryAsgiApp` rejects paths over 256 characters before route tokenization and raw query strings over 4096 bytes before `parse_qsl`; `parse_qsl` receives a bounded field count before authentication | focused hardening regressions prove oversized paths never reach route tokenization or UUID parsing and oversized queries never reach `parse_qsl` or authentication |
| Reject executable scalar subtypes before parsing | ASGI `path` and `query_string` must be exact built-in `str` and `bytes`; subclasses fail closed before `len`, `strip`, or `decode` can dispatch caller-defined behavior | trapping `str`/`bytes` subclasses raise if their overrides execute; the HTTP boundary must return 404/400 with zero authentication calls |
| Validate caller-controlled semantics before protected work | route, query, operational UUIDs, UTC cutoff, purpose, and fields are validated before authentication | malformed input cases prove no authenticator or read-port call |
| Authenticate one bearer credential and canonical principal | existing `_authorization_header`/`extract_bearer_token` contracts plus exact `AuthenticatedPrincipal` runtime check | rejected credentials return 401; unexpected backend failure and noncanonical principal return opaque 500 before the governed service/persistence boundary |
| Preserve the published backend-error contract | authentication-backend failures log one opaque support reference and return that same reference inside a complete `ErrorResponse`; the current Position-stack shared JSON emitter is a passthrough and receives only arguments in its exact signature | focused regression requires `error`, `error_code`, `message`, `next_action`, and `support_reference`, with no secret-bearing exception detail; support-reference compatibility guard requires the route log and payload reference to remain equal |
| Correlate unexpected persistence failures without disclosure | unexpected protected-read failures use a dedicated Position-history ERROR record containing route, tenant, exception type, and the same opaque support reference returned in the complete 500 envelope; exception messages are not logged or returned | end-to-end failing-read regression requires one ERROR record whose reference equals the response reference while a secret-bearing backend message is absent from the client payload and log message |
| Keep synchronous persistence off the ASGI event loop | the synchronous `read_position_history()` service and PostgreSQL adapter execute through `asyncio.to_thread(...)`; worker exceptions propagate to the existing response mapping | focused regression records the protected read-port thread and requires it to differ from the event-loop thread |
| Use least privilege and exact purpose | `orgmetra.people.position_history.read` plus `read_position_history()` policy binding | disallowed fields return 403 before the port is called |
| Preserve bitemporal scope | `known_at` is an exact UTC system-recorded cutoff passed to the Position-history service | call capture and service/real PostgreSQL cutoff tests |
| Minimize the response | `resource_reference` plus authorized `entries[].fields` only | successful and empty-result response assertions; no Person/Employment/Assignment joins |
| Fail closed without disclosure | stable 400/401/403/409/500 client-safe envelopes and opaque support reference | integrity, identity-backend, and secret-bearing persistence failures assert no internal details |
| Publish the same customer contract | OpenAPI route, parameters, schema, scope, and responses | Python/Node structural OpenAPI mutation tests |
| Keep evidence on the exact candidate | consolidated Foundation CI owns repository acceptance; the former feature-local workflow is retired | final protected-parent exact head must reacquire Foundation plus central security/review gates; predecessor results do not transfer |

## Test-first chain

1. **Historical contract-only child head:** `86cc40b1` adds HTTP regressions while `orgmetra_people_api.position_history_http` is absent.
2. **Historical expected RED:** focused collection fails with `ModuleNotFoundError` at that owning module boundary; this remains development evidence only.
3. **Transport implementation:** separate ASGI adapter, package-root export, and OpenAPI customer contract.
4. **Hardening test-only head:** `d119bb8703c5904db5535f3dfbce4f1d2e5ccc1d` adds regressions for oversized path/query input, unexpected identity-backend failure, and noncanonical principal objects.
5. **Hardening causal repair:** `7feeccac56688a1c94f40fa5f43c8f032c8bf834` bounds UUID/query parser work, validates the exact principal before the governed service call, and converts identity-backend exceptions to non-disclosing 500 responses.
6. **CI ownership repair:** `8d3bcdee59e3c01f699d00bd1db3a1051f3248ae` removes the superseded Position-history feature-local workflow instead of resurrecting pre-#161 quality ownership.
7. **Semantic parent reconciliation:** `0b0b1e3de3529a1856dcc4270b48220fd9f2f236` adopts current #153 `dc566a0167d5e8ab17e8fad5e37f86618e4a93e7` as a second parent while preserving only the HTTP/OpenAPI/customer delta and the consolidated Foundation ownership model; `c5e2e5d8b08ad0ea7526ef106740da65b834deda` aligns the ADR lifecycle index.
8. **Route-tokenization RED:** `7ae776750b20f621468a5f188f5dbb0130bf1d97` requires an oversized path to be rejected before `_looks_like_position_history_route()` executes. The preceding implementation invoked the route tokenizer before its length gate.
9. **Route-tokenization causal repair:** `5d239e7db8a0ddb72a367c83e8b285f87421753c` moves the 256-character gate ahead of route decomposition while preserving ordinary 404 routing semantics.
10. **Backend-envelope/event-loop RED:** `88e28cbc565f49992e6de741d356582d20252c30` requires authentication-backend failures to return the complete published error envelope with one opaque support reference and requires the synchronous protected read to run outside the ASGI event-loop thread. At that historical head the Position-stack shared emitter did not accept a `support_reference` keyword and the service call executed directly in `__call__`.
11. **Backend-envelope/event-loop causal repair:** `17adbbf4044a0288489153f72e08179b78b54fd0` puts the generated support reference in the schema-valid payload and awaits `asyncio.to_thread(read_position_history, ...)`. A later sibling-stack comparison incorrectly reintroduced an unsupported keyword; CodeRabbit revalidation identified the tree mismatch and ordinary-forward `66b64fd550230bc20d884919cba1e045bb130c5c` restored the actual Position-stack emitter contract. `f1e303dc5fa947f9f6b404a609aba313fdce4f6e` remains a compatibility guard, not a claimed RED against this predecessor.
12. **Persistence-observability RED contract:** `d6d8e6469f80793d6a13060abb2a38de256a4b23` requires an unexpected protected-read failure to produce one Position-history ERROR record containing non-secret route/tenant/exception-type metadata and the same support reference returned in the 500 response. The predecessor routes this failure through generic `_send_error(...)`, which emits only an INFO rejection and discards the backend exception type.
13. **Persistence-observability causal repair:** `411ba41631a2f31fa80aaadcb3f15d22aa8c26fe` adds a dedicated persistence-backend error emitter and preserves the existing client-safe envelope while keeping the exception message out of both response and log message. Authorization and integrity failures remain on their existing 403/409 paths.
14. **Executable-scalar RED contract:** `d64f4b09ed24d224a3e1eee168791caa75856733` adds `str`/`bytes` subclasses whose `__len__`, `strip`, and `decode` methods raise. The predecessor accepts those subclasses through `isinstance(...)`, so request parsing can dispatch caller-defined Python behavior before authentication.
15. **Executable-scalar causal repair:** `d48927a99979305153a04fb4545994f6bb57c77e` requires exact built-in `str`/`bytes` at the ASGI path/query ingress. Non-exact path data retains the route-not-found response and non-exact query data retains the invalid-request response, both before authentication.
16. **Outer-scope authority RED contract:** issue #328 and test-only `e0500d1e538ff08b9dc0375d8a4b399e040060c3` add a `dict` subtype that traps mapping access and `str` subtypes that trap equality/inequality. The predecessor calls `scope.get(...)` and compares `type`/`method` directly, so these cases expose executable caller behavior before the intended transport authority gates.
17. **Outer-scope authority causal repair:** `45abf5082cb9eda10db323dd8ae6a6e914d60542` requires `type(scope) is dict` before any lookup, exact built-in `str` before comparing the scope type or method, preserves the existing 405 method response, and keeps authentication/persistence untouched for rejected representations.

## Security, availability, and data boundary

The route reads only authorized Position-version fields and the already-governed
Position/Job/organization lineage. It does not join Person, Employment,
Assignment, compensation, candidate, performance, credential, prompt, or model
output data. It performs no write, audit/outbox mutation, or high-impact
employment decision. Identity and persistence backend failures are logged only
with non-secret metadata and one opaque support reference; exception messages and
bearer tokens are not returned to the client. The outer ASGI scope is accepted
only as an exact built-in `dict`, and route-control scalars are accepted only as
exact built-in strings before comparison. Transport path/query scalars are also
accepted only in their exact interpreter-built-in forms before length/tokenization
or decode work. These gates prevent caller-defined container/scalar behavior from
becoming a pre-authentication execution capability. The worker-thread offload
changes only scheduling of the synchronous service call; authorization and the
short read-only PostgreSQL transaction remain owned by #152/#153 and exceptions
retain their existing 403, 409, or opaque 500 mapping.

The offload prevents synchronous DB I/O from monopolizing the ASGI event loop, but
it is not performance acceptance. The buyer path still requires exact-candidate
k6/E2E measurement and p95 evidence under production-equivalent connection/pool
settings before the repository can claim the <=20 ms target.

## Current evidence boundary

#154 remains an ordinary descendant of current #153: its direct base is
`dc566a0167d5e8ab17e8fad5e37f86618e4a93e7`, with no parent delta intentionally
copied into this HTTP lane. Current production repair head is
`45abf5082cb9eda10db323dd8ae6a6e914d60542`; later documentation-only commits do
not change that source/test contract. These short-lived/current heads have no
PR-triggered Foundation run because the PR targets #153 rather than protected
`develop`; that absence is neither hosted RED nor GREEN. The current exact head
must not inherit predecessor Foundation, security, model-review, or feature-local
GREEN. Those gates must be reacquired after #152/#153 reach the protected lane and
#154 is ordinary-forward retargeted onto that resulting protected truth.

## Out of scope

- Pagination or export workflows.
- Position correction or mutation workflows.
- Cross-service application-database queries.
- Browser UI, Storybook, or Figma work; this slice is a transport contract.
- Release, tag, publication, or protected-default-branch authority.
