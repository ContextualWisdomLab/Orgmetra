# CHANGELOG

All notable changes to Orgmetra will be documented in this file.

## [Unreleased]

### Added

- Foundation product baseline for Orgmetra as an evidence-centered HRIS/HCM.
- CWL federated integration boundary map.
- Bitemporal HRIS data contract with stable identity anchors and versioned person-name facts.
- Core ERD, UML, PRD, TRD, user stories, storyboard, wireframes, Storybook inventory, security, test, and operability baseline.
- Versioned selection-decision evidence records and complete mutation-context OpenAPI schemas.
- Manifest digest, byte-count, and line-count validation.

### Changed

- Canonicalized service identifiers as two-or-more-word `snake_case` across architecture, deployment, ACL, metrics, and client contracts.
- Separated fast-mlsirm, TEPP, and Psychometrics Commons into immutable external scientific contracts.
- Defined 100% owned production statement and branch coverage as a CI gate where the pinned toolchain exposes those metrics.

### Security

- Purpose-bound PII access contract.
- LLM output constrained to draft evidence.
- No direct cross-service application-table access.
- Service-owned database schemas and roles inside the initially shared physical PostgreSQL cluster.
- Database guards for reversed temporal intervals and append-only candidate-worker, selection-decision, and decision-evidence records.
- Keyverse outage policy that blocks PII and high-risk actions when current authorization cannot be verified.
- Cross-tenant threat, denial evidence, and negative authorization test contracts.

### Notes

- The protected default branch contains only the minimal bootstrap commit. This baseline is proposed through `feat/foundation-product-baseline` and becomes shipped truth only after review and merge.
