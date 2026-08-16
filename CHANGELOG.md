# CHANGELOG

All notable changes to Orgmetra will be documented in this file.

## [Unreleased]

### Added

- Independently importable `orgmetra-domain` package for bitemporal HRIS invariants.
- Deterministic business-time/knowledge-time historical fact resolution that fails closed on ambiguous overlapping versions.
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

### Security

- Purpose-bound PII access contract.
- LLM output constrained to draft evidence.
- No direct cross-service database access.
- Candidate-to-worker relink failures now return a bounded adapter-safe message with no candidate or person identifiers.

### Notes

- The protected default branch contains only the minimal bootstrap commit. PR #8 is the canonical foundation baseline; this domain slice remains stacked behind it and becomes shipped truth only after dependency-ordered review, fresh exact-head checks, and merge.
