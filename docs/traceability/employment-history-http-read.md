# Employment-history HTTP read traceability

**Lifecycle status:** Active stacked PR #155 only. This document does not claim protected-`develop` integration.

## Buyer problem

PR #149 defines an authorized Employment-history read, but a customer still
needs one stable HTTP boundary to request that history without deployment-
specific parsing, authentication, or serialization code widening the data
surface.

## Requirement-to-evidence matrix

| Requirement | Production boundary | Regression |
| --- | --- | --- |
| Validate before protected work | `EmploymentHistoryAsgiApp` parses route, query, UUIDs, UTC cutoff, purpose, and fields before authentication | malformed input cases prove no authenticator or read-port call |
| Authenticate one bearer credential | existing `_authorization_header` and `extract_bearer_token` contracts | missing, duplicate, malformed, non-ASCII, and rejected credentials return 401 |
| Use least privilege and exact purpose | `orgmetra.people.employment_history.read` plus `read_employment_history()` policy binding | disallowed fields return 403 before the port is called |
| Preserve bitemporal scope | `known_at` is an exact UTC system-recorded cutoff passed to the Employment-history service | call capture and service bitemporal tests |
| Minimize the response | `resource_reference` plus authorized `entries[].fields` only | successful and empty-result response assertions; no Person/Position/Assignment joins |
| Fail closed without disclosure | stable 400/401/403/409/500 client-safe envelopes and opaque support reference | integrity and secret-bearing backend failures assert no internal details |
| Publish the same customer contract | OpenAPI route, parameters, response schema, scope, and responses | Python/Node structural OpenAPI mutation tests |
| Keep evidence on the exact candidate | canonical Foundation checks out the PR head and executes the complete People suite when the stack returns to a protected-`develop` PR boundary | compile, exact 100% statement/branch coverage, repository validation, and clean checkout |

## Test-first chain

1. **Contract-only child head:** `6c2d6b89` adds HTTP regressions while `orgmetra_people_api.employment_history_http` is absent.
2. **Expected RED:** focused collection fails with `ModuleNotFoundError` at that owning module boundary; this is distinct from a missing dependency-path invocation.
3. **Implementation:** add the smallest separate ASGI adapter, package-root export, OpenAPI contract, and structural OpenAPI regressions.
4. **Repository-quality repair:** protected #161 consolidated repository-owned validation into Foundation. Current branch commit `ec2389f47f2ed6b0b10ee0a7ce5d931770a09dcf` retires the obsolete Employment-history leaf workflow instead of recreating a second owner.
5. **Required verification:** ordinary non-force reconciliation with current #149, deterministic manifest reseal from the resolved bytes, then exact-head Foundation/security/CodeQL/model-review and qualifying independent-review evidence. Pre-consolidation results do not transfer.

## Stack authority

Current canonical Employment-history application owner #149 is
`93f415922592734d9d4ba3afb69a8633ecb3de15` on #55. This HTTP branch was
created from older #149 snapshot `44c83128701f1985f8566b39cbf837c7b20f0111`.
The HTTP feature remains valid, but its overlapping changelog, manifest,
repository validators, People README/exports, and OpenAPI provenance must be
semantically reconciled with current parent truth before integration. The
retired leaf workflow must remain absent throughout that reconciliation.

## Security and data boundary

The route reads only authorized Employment-version fields and the already-
governed Person/Employment lineage. It does not join Position, Assignment,
compensation, candidate, performance, credential, prompt, or model-output data.
It performs no write, audit/outbox mutation, or high-impact employment decision.

## Out of scope

- Pagination or export workflows.
- Employment correction or mutation workflows.
- Cross-service application-database queries.
- Browser UI, Storybook, or Figma work; this slice is a transport contract.
- Release, tag, publication, or protected-default-branch authority.
