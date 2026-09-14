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
| Bound untrusted transport input before protected work | `PositionHistoryAsgiApp` rejects paths over 256 characters before route tokenization and raw query strings over 4096 bytes before `parse_qsl`; `parse_qsl` receives a bounded field count before authentication | focused hardening regressions prove oversized paths never reach route tokenization or UUID parsing and oversized queries never reach `parse_qsl` or authentication |
| Validate caller-controlled semantics before protected work | route, query, operational UUIDs, UTC cutoff, purpose, and fields are validated before authentication | malformed input cases prove no authenticator or read-port call |
| Authenticate one bearer credential and canonical principal | existing `_authorization_header`/`extract_bearer_token` contracts plus exact `AuthenticatedPrincipal` runtime check | rejected credentials return 401; unexpected backend failure and noncanonical principal return opaque 500 before the governed service/persistence boundary |
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

## Security and data boundary

The route reads only authorized Position-version fields and the already-governed
Position/Job/organization lineage. It does not join Person, Employment,
Assignment, compensation, candidate, performance, credential, prompt, or model
output data. It performs no write, audit/outbox mutation, or high-impact
employment decision. Identity-backend failures are logged only with non-secret
metadata and an opaque support reference; exception messages and bearer tokens are
not returned to the client.

## Current evidence boundary

#154 is now an ordinary descendant of current #153: its merge base is
`dc566a0167d5e8ab17e8fad5e37f86618e4a93e7`, with no parent commits behind. The
semantic reconciliation removed the retired feature workflow and reduced the PR
delta to the Position HTTP/OpenAPI/customer contract plus its feature evidence.
This is still a stacked feature branch, not protected-`develop` acceptance. The
current exact head must not inherit predecessor Foundation, security, model-review,
or feature-local GREEN; those gates must be reacquired after #152/#153 reach the
protected lane and #154 is retargeted onto that resulting protected truth.

## Out of scope

- Pagination or export workflows.
- Position correction or mutation workflows.
- Cross-service application-database queries.
- Browser UI, Storybook, or Figma work; this slice is a transport contract.
- Release, tag, publication, or protected-default-branch authority.
