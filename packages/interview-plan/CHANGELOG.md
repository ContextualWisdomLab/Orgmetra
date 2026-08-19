# Changelog

## 0.1.0 - Unreleased

### Added

- Candidate-neutral `StructuredInterviewPlan` binding an approved requisition and Job to exact job-analysis, question-set, question-to-competency mapping, rating-anchor, competency, and interviewer-panel evidence.
- Fail-closed direct-construction validation, deterministic canonical JSON/SHA-256 audit correlation, explicit human approval state, and 100% owned statement/branch regression coverage.

### Changed

- Require a separately identified and SHA-256-bound question-to-competency mapping artifact so question count alone cannot be treated as proof that every governed competency is assessed.

### Security and privacy

- Require canonical non-sentinel UUID suffixes for every trust-bearing scalar and collection reference, rejecting human-readable/value-bearing metadata before serialization.
- Close `reason_code` to the reviewed non-sensitive `approved_requisition_interview` value.
- Redact `StructuredInterviewPlan` representation so routine logs and assertion failures do not expose sensitive correlations or evidence digests.
