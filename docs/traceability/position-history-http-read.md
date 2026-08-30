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
| Validate before protected work | `PositionHistoryAsgiApp` parses route, query, UUIDs, UTC cutoff, purpose, and fields before authentication | malformed input cases prove no authenticator or read-port call |
| Authenticate one bearer credential | existing `_authorization_header` and `extract_bearer_token` contracts | missing, duplicate, malformed, non-ASCII, and rejected credentials return 401 |
| Use least privilege and exact purpose | `orgmetra.people.position_history.read` plus `read_position_history()` policy binding | disallowed fields return 403 before the port is called |
| Preserve bitemporal scope | `known_at` is an exact UTC system-recorded cutoff passed to the Position-history service | call capture and service/real PostgreSQL cutoff tests |
| Minimize the response | `resource_reference` plus authorized `entries[].fields` only | successful and empty-result response assertions; no Person/Employment/Assignment joins |
| Fail closed without disclosure | stable 400/401/403/409/500 client-safe envelopes and opaque support reference | integrity and secret-bearing backend failures assert no internal details |
| Publish the same customer contract | OpenAPI route, parameters, schema, scope, and responses | Python/Node structural OpenAPI mutation tests |
| Keep evidence on the exact candidate | dedicated workflow checks PR head and complete People suite | compile, exact 100% statement/branch coverage, and clean checkout |

## Test-first chain

1. **Contract-only child head:** `86cc40b1` adds HTTP regressions while `orgmetra_people_api.position_history_http` is absent.
2. **Expected RED:** focused collection fails with `ModuleNotFoundError` at that owning module boundary; this is distinct from the missing dependency-path invocation.
3. **Implementation:** add the smallest separate ASGI adapter, package-root export, OpenAPI contract, and dedicated quality workflow.
4. **Verification:** run the full People API suite with exact statement and branch coverage, repository validation, actionlint, CodeGraph synchronization, and current-head hosted checks.

## Security and data boundary

The route reads only authorized Position-version fields and the already-governed
Position/Job/organization lineage. It does not join Person, Employment,
Assignment, compensation, candidate, performance, credential, prompt, or model
output data. It performs no write, audit/outbox mutation, or high-impact
employment decision.

## Out of scope

- Pagination or export workflows.
- Position correction or mutation workflows.
- Cross-service application-database queries.
- Browser UI, Storybook, or Figma work; this slice is a transport contract.
- Release, tag, publication, or protected-default-branch authority.
