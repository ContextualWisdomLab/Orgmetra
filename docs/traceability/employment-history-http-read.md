# Employment-history HTTP read traceability

**Lifecycle status:** Active stacked PR #155 only. This document does not claim protected-`develop` integration.

## Buyer problem

PR #149 defines an authorized Employment-history read, but a customer still needs one stable HTTP boundary without deployment-specific parsing, authentication, or serialization code widening the data surface.

## Requirement-to-evidence matrix

| Requirement | Production boundary | Regression |
| --- | --- | --- |
| Validate before protected work | `EmploymentHistoryAsgiApp` parses route, query, UUIDs, UTC cutoff, purpose, and fields before authentication | malformed input cases prove no authenticator or read-port call |
| Bound caller-controlled transport work | path length is capped before route tokenization; query bytes and parser field count are bounded before authentication | oversized path/query regressions prove parser/identity/persistence are not reached |
| Preserve authenticated identity integrity | only exact `AuthenticatedPrincipal` is accepted; backend malfunction becomes opaque 500 | arbitrary principal and secret-bearing authenticator failures stop before persistence |
| Preserve one support reference | route generates/logs one opaque reference and passes it into canonical #55 `_send_json`, which enriches the published `ErrorResponse` without changing the reference | `a38c0b...` compares the Employment route ERROR-log `support_reference` with the response value |
| Keep synchronous persistence off the ASGI event loop | synchronous `read_employment_history()` service/PostgreSQL work executes through `asyncio.to_thread(...)` | `d998cd...` records the read-port thread and requires it to differ from the event-loop thread |
| Use least privilege and exact purpose | `orgmetra.people.employment_history.read` plus `read_employment_history()` policy binding | disallowed fields return 403 before port call |
| Preserve bitemporal scope | exact UTC `known_at` passed to service | service and PostgreSQL cutoff contracts |
| Minimize response | `resource_reference` plus authorized `entries[].fields` only | success/empty-response tests; no Position/Assignment joins |
| Keep evidence on exact candidate | consolidated Foundation owns repository acceptance after protected-base retarget | predecessor and feature-local verdicts do not transfer |

## Test-first and reconciliation chain

1. Historical contract-only `6c2d6b89` established the absent-module RED; later implementation added the ASGI/OpenAPI boundary.
2. `2bcf5586745b57b19b65a9b9c801497a409c3b66` added transport-boundary regressions; `15cd1ec7680dd059fa926bad88d7a89c0598716f` added bounded input, exact principal, and client-safe backend handling.
3. Ordinary parent reconciliation adopted #149/#55 truth and retired the obsolete feature-local quality owner.
4. `8a367eb8885807dc21581c55e6a21b10e2ca5799` proved oversized paths still reached route tokenization; `99c3ec578a57c31f039cab70b6e3a90a4b85623a` moved the length gate ahead of `strip()`/`split()`.
5. Sibling #154 review exposed a synchronous-service-on-ASGI-loop risk. This finding independently reproduces in #155: predecessor `03030dbccba3b6044e2b4d8201203f309d4f40de` directly calls `read_employment_history()`. Test-only `d998cd684adee518b04ddc37cfad7c17ea151d8c` requires the protected read to run off the event-loop thread; `3432b08b67f28cf5e665346494104ec15d523590` introduces `asyncio.to_thread(...)`.
6. The sibling #154 `support_reference` signature finding does **not** reproduce in #155. #155 already inherits canonical #55 `_send_json(..., support_reference=...)`, so the predecessor backend path already returns a schema-enriched response through the shared emitter. The initial sibling-style source edit in `3432b08...` incorrectly omitted that argument, causing the shared emitter to mint a second reference.
7. Test-first `a38c0b2286aff93ec19a766bcd63927754648e7b` requires the Employment ERROR-log reference to equal the returned `support_reference`. Causal repair `15220135234107de82c481816f19749198c61012` restores canonical shared-emitter ownership and passes the pre-generated reference through both backend-error and generic `_send_error` paths.
8. ADR correction `06390b0d5bc14fdd620ba6f83d3a7973bf0ed9a9` removes the false sibling-signature claim and records the actual checked owner contract.
9. Final acceptance remains deferred until the owner stack reaches protected `develop`, at which point exact-head Foundation/security/SAST/CodeQL/model review, qualifying independent review, and applicable latency evidence must be reacquired.

## Stack authority

Canonical Employment-history application owner #149 remains `d2e7d0c1fc038bf151466ad8e1ce1a3074d2d750` on #55. #155 changes only its HTTP source/tests and feature ADR/traceability; the shared JSON emitter remains parent-owned and is consumed rather than copied.

## Security, availability, and data boundary

The route reads only authorized Person/Employment history and performs no mutation or employment decision. Authentication backend errors retain one non-secret support reference across route logging and client response. Synchronous Employment/PostgreSQL work is worker-thread isolated from ASGI, but this is not a p95 claim; production-equivalent k6/E2E measurement remains required.

## Out of scope

- Pagination/export.
- Employment correction or mutation.
- Cross-service application-database queries.
- Browser UI/Storybook/Figma for this transport-only slice.
- Release/tag/protected-branch authority.
