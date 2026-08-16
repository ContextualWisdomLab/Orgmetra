# CHANGELOG

All notable changes to Orgmetra will be documented in this file.

## [Unreleased]

### Added

- Independently importable `orgmetra-domain` package for bitemporal HRIS invariants.
- Durable organization-unit and job-profile anchors with separate bitemporal version records so Organization, Job, Position, and Assignment remain distinct HRIS concepts.
- Multiple-membership assignment allocation validation with half-open effective intervals.
- Append-only, idempotent candidate-to-worker linkage.
- Hash-locked Python 3.11-3.14 quality workflow with exact 100% production statement/branch coverage and public docstring checks.
- Foundation product baseline for Orgmetra as evidence-centered HRIS/HCM.
- CWL federated integration boundary map.
- Bitemporal HRIS data contract.
- Core ERD, UML, PRD, TRD, user stories, storyboard, wireframes, Storybook inventory, security, test, and operability baseline.

### Changed

- Organization and job mutable descriptions now live in version records rather than durable identity anchors, preserving normalized history and stable position references.
- Effective and system-recorded intervals are non-empty half-open periods; equal start/end bounds are rejected.
- People API route handlers now inject `PurposeContext` and the repository through runtime `Depends` defaults so callers cannot supply those objects as query fields.
- People API now exposes candidate and hire-link reads plus create/get employment so an authorized HR actor can complete the hire-to-employment path without caller-owned knowledge time.

### Fixed

- People API Quality no longer fails with HTTP 422 on every protected route when FastAPI 0.116 interprets postponed annotations as query parameters.
- Bearer token parsing now splits only on the first ASCII space so C0 separators such as `\\x1f` remain visible and are rejected.
- People API CI now pins the same Python 3.14-compatible Pydantic lock as Keyverse authorization and includes `certifi` so `pip check` can close the httpx dependency set.
- People API OpenAPI tests now whitelist published parameters and reject attacker query names instead of only blacklisting `context`, `request`, and `repository_port`.

### Security

- Purpose-bound PII access contract.
- LLM output constrained to draft evidence.
- No direct cross-service database access.
- Reject malformed, duplicate, or non-verification JWK `key_ops` declarations before constructing a signing key.

### Notes

- The protected default branch contains only the minimal bootstrap commit. This baseline is proposed through `feat/foundation-product-baseline` and becomes shipped truth only after review and merge.
