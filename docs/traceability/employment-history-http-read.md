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
| Bound caller-controlled transport work | path length is capped at 256 characters before route tokenization; raw query at 4096 bytes before `parse_qsl`; query field count is bounded before authentication | boundary-hardening regressions prove oversized path never reaches route tokenization and oversized query never reaches `parse_qsl`, authenticator, or read port |
| Authenticate one bearer credential | existing bounded `_authorization_header` and `extract_bearer_token` contracts | missing, duplicate, malformed, non-ASCII, and rejected credentials return 401 |
| Preserve authenticated identity integrity | only exact `AuthenticatedPrincipal` is accepted after authentication; unexpected identity-backend failures become client-safe 500 responses with opaque support references | arbitrary principal result and secret-bearing authenticator exception both fail before persistence; response omits backend secret text |
| Use least privilege and exact purpose | `orgmetra.people.employment_history.read` plus `read_employment_history()` policy binding | disallowed fields return 403 before the port is called |
| Preserve bitemporal scope | `known_at` is an exact UTC system-recorded cutoff passed to the Employment-history service | call capture and service bitemporal tests |
| Minimize the response | `resource_reference` plus authorized `entries[].fields` only | successful and empty-result response assertions; no Person/Position/Assignment joins |
| Fail closed without disclosure | stable 400/401/403/409/500 client-safe envelopes and opaque support reference | integrity, persistence, and identity-backend failures assert no internal details |
| Publish the same customer contract | OpenAPI route, parameters, response schema, scope, and responses | Python/Node structural OpenAPI mutation tests |
| Keep evidence on the exact candidate | canonical Foundation checks out the PR head and executes the complete People suite when the stack returns to a protected-`develop` PR boundary | compile, exact 100% statement/branch coverage, repository validation, and clean checkout |

## Test-first and reconciliation chain

1. **Contract-only child head:** `6c2d6b89` added HTTP regressions while `orgmetra_people_api.employment_history_http` was absent.
2. **Expected RED:** focused collection failed with `ModuleNotFoundError` at that owning module boundary; this is distinct from a missing dependency-path invocation.
3. **Implementation:** the smallest separate ASGI adapter, package-root export, OpenAPI contract, and structural OpenAPI regressions were added.
4. **Repository-quality repair:** protected #161 consolidated repository-owned validation into Foundation. Commit `ec2389f47f2ed6b0b10ee0a7ce5d931770a09dcf` retired the obsolete Employment-history leaf workflow instead of recreating a second owner.
5. **Parent reconciliation:** ordinary two-parent merge `32ce60e60d718f4007dc4bc0a42d370e5470b60f` adopted the then-current #149 without force-push or destructive rebase while preserving the complete HTTP/OpenAPI/security/docs/tests delta.
6. **Provenance repair:** the merge removed obsolete pre-#161 leaf-workflow assumptions, corrected stale quality-owner claims, and resealed `manifest.json` from the resolved required-artifact bytes.
7. **Transport RED contract:** `2bcf5586745b57b19b65a9b9c801497a409c3b66` adds focused regressions requiring unexpected identity-backend failure, arbitrary authenticator result, oversized path, and oversized query to fail closed before protected persistence.
8. **Minimum causal repair:** `15cd1ec7680dd059fa926bad88d7a89c0598716f` adds bounded path/query handling, exact `AuthenticatedPrincipal`, and non-disclosing identity-backend failure handling.
9. **Owner-lineage restack:** ordinary two-parent merge `554e223ee5133c2a30646c1c048cc004e7f1eb36` adopts current #149 `d2e7d0c1fc038bf151466ad8e1ce1a3074d2d750`, which already carries canonical #55's retained-UUID scalar-authority repair.
10. **Route-tokenization RED:** `8a367eb8885807dc21581c55e6a21b10e2ca5799` requires an oversized path to be rejected before `_looks_like_employment_history_route()` executes. The preceding implementation called the route tokenizer before its size gate.
11. **Route-tokenization causal repair:** `99c3ec578a57c31f039cab70b6e3a90a4b85623a` moves the 256-character gate ahead of route decomposition while retaining ordinary 404 routing semantics.
12. **Required verification:** after the owner stack returns to the canonical protected-`develop` PR boundary, reacquire exact-head Foundation/security/SAST/CodeQL/model-review and qualifying independent-review evidence. Pre-consolidation and predecessor-head results do not transfer.

## Stack authority

Canonical Employment-history application owner #149 is
`d2e7d0c1fc038bf151466ad8e1ce1a3074d2d750` on #55. #155 ordinary-forward
adopted that owner in `554e223ee5133c2a30646c1c048cc004e7f1eb36`; the current HTTP lineage remains
0-behind that direct base and keeps the retired feature-local workflow absent.
The later route-tokenization RED/repair changes only #155-owned transport/tests
and their ADR/traceability evidence; no parent-owned source is copied downstream.

## Security and data boundary

The route reads only authorized Employment-version fields and the already-
governed Person/Employment lineage. It does not join Position, Assignment,
compensation, candidate, performance, credential, prompt, or model-output data.
It performs no write, audit/outbox mutation, or high-impact employment decision.

Caller-controlled path/query work is bounded before route/query parsing, identity,
or persistence work. Authentication failure remains distinguishable as 401,
while identity-backend malfunction or a noncanonical principal object fails closed
as a generic 500 and never reaches authorization/persistence. Bearer credentials
and backend exception text are not copied into customer responses.

## Out of scope

- Pagination or export workflows.
- Employment correction or mutation workflows.
- Cross-service application-database queries.
- Browser UI, Storybook, or Figma work; this slice is a transport contract.
- Release, tag, publication, or protected-default-branch authority.
