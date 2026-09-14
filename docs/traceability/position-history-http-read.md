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
| Bound untrusted transport input before protected work | `PositionHistoryAsgiApp` rejects paths over 256 characters and raw query strings over 4096 bytes; `parse_qsl` receives a bounded field count before authentication | focused hardening regressions prove oversized paths never reach UUID parsing and oversized queries never reach `parse_qsl` or authentication |
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
4. **Current hardening test-only head:** `d119bb8703c5904db5535f3dfbce4f1d2e5ccc1d` adds regressions for oversized path/query input, unexpected identity-backend failure, and noncanonical principal objects.
5. **Causal repair:** `7feeccac56688a1c94f40fa5f43c8f032c8bf834` bounds parser work, validates the exact principal before the governed service call, and converts identity-backend exceptions to non-disclosing 500 responses.
6. **CI ownership repair:** `8d3bcdee59e3c01f699d00bd1db3a1051f3248ae` removes the superseded Position-history feature-local workflow instead of resurrecting pre-#161 quality ownership.

## Security and data boundary

The route reads only authorized Position-version fields and the already-governed
Position/Job/organization lineage. It does not join Person, Employment,
Assignment, compensation, candidate, performance, credential, prompt, or model
output data. It performs no write, audit/outbox mutation, or high-impact
employment decision. Identity-backend failures are logged only with non-secret
metadata and an opaque support reference; exception messages and bearer tokens are
not returned to the client.

## Current evidence boundary

#154 is still stacked on a stale #153 predecessor and therefore is not acceptance
ready. The current-parent semantic reconciliation must preserve the HTTP/OpenAPI
feature delta, keep the retired leaf workflow absent, merge the Position-history
OpenAPI validators into the consolidated foundation validators, currentize
CHANGELOG/Test Strategy wording, and reseal `manifest.json` from the final bytes.
No current-head Foundation GREEN is claimed before that reconciliation reaches a
protected-`develop` PR lane.

## Out of scope

- Pagination or export workflows.
- Position correction or mutation workflows.
- Cross-service application-database queries.
- Browser UI, Storybook, or Figma work; this slice is a transport contract.
- Release, tag, publication, or protected-default-branch authority.
