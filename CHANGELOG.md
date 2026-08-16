# CHANGELOG

All notable changes to Orgmetra will be documented in this file.

## [Unreleased]

### Added

- Independently importable `orgmetra-domain` package for bitemporal HRIS invariants.
- Deterministic business-time/knowledge-time historical fact resolution that fails closed on ambiguous overlapping versions.
- Identity-scoped historical resolution so two people, jobs, or units are never treated as one ambiguous fact.
- Durable organization-unit and job-profile anchors with separate bitemporal version records so Organization, Job, Position, and Assignment remain distinct HRIS concepts.
- Durable employment and position anchors with separate bitemporal status versions so a correction does not look like a second employment or a new seat.
- Recorded-time assignment portfolio validation, write-time history checks, covering-employment validation, and position capacity checks for job-share.
- Organization hierarchy cycle rejection for visible A→B→A parent links.
- Multiple-membership assignment allocation validation with half-open effective intervals.
- Append-only, idempotent candidate-to-worker linkage.
- ADR 0006 for recorded-time assignment integrity and versioned employment/position. Persistence PR #5 keeps ADR 0005.
- Hash-locked Python 3.11-3.14 quality workflow with exact 100% production statement/branch coverage and public docstring checks.
- Foundation product baseline for Orgmetra as evidence-centered HRIS/HCM.
- CWL federated integration boundary map.
- Bitemporal HRIS data contract.
- Core ERD, UML, PRD, TRD, user stories, storyboard, wireframes, Storybook inventory, security, test, and operability baseline.

### Changed

- Organization and job mutable descriptions now live in version records rather than durable identity anchors, preserving normalized history and stable position references.
- Employment and position mutable status now live in version records rather than durable identity anchors.
- `validate_assignment_portfolio()` requires timezone-aware `known_at` and ignores rows that were not visible at that knowledge time.
- `resolve_bitemporal_fact()` requires `identity_of` and rejects mixed-identity collections; use `resolve_bitemporal_facts_by_identity()` to review each identity.
- `AssignmentRecord` requires `employment_record_id` and rejects ratios that cannot persist as `numeric(5,4)`.
- Effective and system-recorded intervals are non-empty half-open periods; equal start/end bounds are rejected.

### Security

- Purpose-bound PII access contract.
- LLM output constrained to draft evidence.
- No direct cross-service database access.
- Candidate-relink and allocation errors omit HR identifiers, dates, and ratios so adapters can expose them without leaking schedule detail.

### Notes

- The protected default branch contains only the minimal bootstrap commit. PR #8 is the canonical foundation baseline; this domain slice remains stacked behind it and becomes shipped truth only after dependency-ordered review, fresh exact-head checks, and merge.
