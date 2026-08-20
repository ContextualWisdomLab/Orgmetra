# ADR 0015: Product and technical gap baseline

- Status: Accepted on active development branch
- Date: 2026-08-20
- Owners: Orgmetra Product / Platform

## Context

Orgmetra has a strong evidence and integrity foundation, but its documentation has repeatedly mixed protected `develop` truth, active pull requests, accepted architecture, and planned product work. A buyer must be able to tell which workflow can be executed today, which is review-ready but unmerged, and which is only a design promise.

The product baseline also uses a Figma wireframe source and repeated HR actions. The source file key is `xu1ZK1zmtFcDep95R8oE9O`; it is recorded here so design-to-code work can be traced to one design source. The implementation must continue to use `packages/design-tokens/` rather than inventing one-off action colors.

## Decision

1. `docs/product-technical-gap-baseline.md` is the current evidence ledger for buyer-visible product gaps and technical gaps.
2. Every capability in the ledger has one maturity value: `implemented_on_protected_develop`, `implemented_on_active_pr`, `accepted_architecture`, `planned`, `research_only`, `superseded`, or `out_of_scope`.
3. Protected-default-branch claims require current `develop` evidence. An OpenAPI definition, a passing predecessor workflow, a local branch, or a PR body cannot be presented as shipped runtime behavior.
4. The authoritative People mutation and confirmed-hire paths are now the first protected integration lane. They remain the dependency for browser workflows and must preserve tenant authorization, idempotency, bitemporal history, human confirmation, audit, and outbox atomicity.
5. Job-analysis persistence/API work now converges on the single current PR #38 model, with migration 0013 and its own ADR; a second Task/FJA/KSAO store must not be introduced.
6. Statistical validity computation remains a separate scientific boundary. Integrity linkage is necessary evidence hygiene, not a validity result. Any future numerical kernel is Rust-first and must publish CPU reference, multilevel/multiple-membership, temporal, uncertainty, convergence, and GPU-parity evidence where GPU execution is material.
7. Figma remains a design-system input, while the local Storybook runtime is executable component/state evidence rather than evidence of a connected customer UI. A release claim requires executable UI, keyboard/accessibility checks, interaction tests, and browser evidence for the owning workflow.

## Consequences

- Product and engineering planning use the same gap IDs and acceptance evidence.
- Review, merge, release, and scheduled-loop automation can consume one small status contract instead of inferring maturity from filenames or PR titles.
- Figma remains traceable without copying a design file into the repository.
- A gap can be closed only when the required runtime, documentation, tests, and protected-branch evidence all exist.

## References

See `docs/doctoring/REFERENCES.md` for APA 7 sources, including ISO 30405:2023, NIST AI RMF 1.0, AICPA Trust Services Criteria, WCAG 2.2, Fugu, Conductor, and TRINITY.
