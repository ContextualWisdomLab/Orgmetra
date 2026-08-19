# Changelog

## 0.1.0 - Unreleased

### Added

- Candidate-neutral `StructuredInterviewPlan` binding an approved requisition and Job to exact job-analysis, question-set, question-to-competency mapping, rating-anchor, competency, and interviewer-panel evidence.
- Fail-closed direct-construction validation, deterministic canonical JSON/SHA-256 audit correlation, explicit human approval state, and 100% owned statement/branch regression coverage.
- Bounded positive `evidence_version` in canonical evidence so materially revised plans have explicit immutable revision identity.

### Changed

- Require a separately identified and SHA-256-bound question-to-competency mapping artifact so question count alone cannot be treated as proof that every governed competency is assessed.
- Revalidate evidence-version changes through direct construction and `dataclasses.replace(...)`; changing the version changes canonical SHA-256 correlation.
- Require canonical non-sentinel UUIDv4 suffixes for every trust-bearing reference; UUIDv1 and other UUID versions now fail closed.

### Security and privacy

- Reject timestamp/node-bearing UUIDv1 reference suffixes as well as human-readable/value-bearing metadata before serialization.
- Close `reason_code` to the reviewed non-sensitive `approved_requisition_interview` value.
- Redact `StructuredInterviewPlan` representation so routine logs and assertion failures do not expose sensitive correlations or evidence digests.
