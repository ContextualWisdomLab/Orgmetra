# CHANGELOG

All notable changes to Orgmetra will be documented in this file.

## [Unreleased]

### Added

- Foundation product baseline for Orgmetra as an evidence-centered HRIS/HCM.
- CWL federated integration boundary map.
- Bitemporal HRIS data contract with stable identity anchors and versioned person-name facts.
- Durable organization/job anchors with normalized bitemporal organization hierarchy and job-definition version records.
- Core ERD, UML, PRD, TRD, user stories, storyboard, wireframes, Storybook inventory, security, test, and operability baseline.
- Effective-dated performance-cycle records linked to criterion observations.
- Versioned selection-decision evidence sets, normalized evidence membership, and validity-study links to exact decisions, evidence, and outcomes.
- PostgreSQL contract tests for bitemporal concurrency, tenant isolation, and decision-evidence sealing.
- Structural OpenAPI mutation tests that bind authorization scopes, command schemas, evidence limits, human confirmation, and client-safe error contracts to their owning operations.
- Manifest digest, byte-count, and line-count validation with a regression preventing Python and Node foundation-artifact inventories from drifting apart.

### Changed

- Canonicalized service identifiers as two-or-more-word `snake_case` across architecture, deployment, ACL, metrics, and client contracts.
- Separated fast-mlsirm, TEPP, and Psychometrics Commons into immutable external scientific contracts.
- Defined 100% owned production statement and branch coverage as a CI gate where the pinned toolchain exposes those metrics.
- Made every baseline OpenAPI mutation declare its own least-privilege Keyverse scope while retaining finer purpose-bound authorization.
- Enforced non-empty half-open effective/system intervals in the database to match the domain contract.
- Bound every current HRIS fact to a tenant using tenant-qualified foreign keys and forced row-level security, including a fail-closed missing-tenant-context contract.
- Made high-impact selection finalization require non-empty versioned evidence and compute the canonical SHA-256 evidence-set digest inside PostgreSQL before sealing the set to exactly one consuming decision.

### Security

- Purpose-bound PII access contract.
- LLM output constrained to draft evidence.
- No direct cross-service application-table access.
- Service-owned database schemas and roles inside the initially shared physical PostgreSQL cluster.
- Database guards for reversed or zero-length temporal intervals and append-only candidate-worker, selection-decision, decision-evidence, and validation-study linkage records.
- Database-level rejection of cross-tenant references, post-decision evidence insertion, caller-supplied open-set evidence digests, empty decision evidence, and sealed evidence-set reuse.
- Keyverse outage policy that blocks PII and high-risk actions when current authorization cannot be verified.
- Cross-tenant threat, denial evidence, and negative authorization test contracts.
- Replaced client-visible internal trace identifiers with random support references and actionable next-step error guidance.

### Notes

- The protected default branch contains only the minimal bootstrap commit. This baseline is proposed through `feat/foundation-product-baseline` and becomes shipped truth only after review and merge.
