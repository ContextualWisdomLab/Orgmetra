# Changelog

## 0.1.0 - Unreleased

### Added

- Candidate-neutral `StructuredInterviewPlan` binding an approved requisition and Job to exact job-analysis, question-set, question-to-competency mapping, rating-anchor, competency, and interviewer-panel evidence.
- Fail-closed direct-construction validation, deterministic canonical JSON/SHA-256 audit correlation, explicit human approval state, and 100% owned statement/branch regression coverage.
- Bounded positive `evidence_version` in canonical evidence so materially revised plans have explicit immutable revision identity.
- Tenant-scope activation regressions requiring authoritative requisition/Job/Job Analysis, evidence-provenance, and panel-actor resolution before use.

### Changed

- Require a separately identified and SHA-256-bound question-to-competency mapping artifact so question count alone cannot be treated as proof that every governed competency is assessed.
- Revalidate evidence-version changes through direct construction and `dataclasses.replace(...)`; changing the version changes canonical SHA-256 correlation.
- Keep packet-owned trust-bearing reference suffixes canonical non-sentinel UUIDv4, while `tenant_record_id` now follows Orgmetra's authoritative canonical non-sentinel operational UUID contract so valid core tenant identities are not rejected by this leaf package.
- Require the host to re-resolve every plan reference in the exact tenant, prove requisition-to-Job-to-job-analysis binding, verify question/rating provenance, and prove resolved panel identities are distinct and eligible/trained before accountable human activation.

### Security and privacy

- Reject timestamp/node-bearing UUIDv1 values in packet-owned trust references as well as human-readable/value-bearing reference metadata before serialization; tenant UUID generation/privacy policy remains owned by the authoritative HRIS boundary.
- Close `reason_code` to the reviewed non-sensitive `approved_requisition_interview` value.
- Redact `StructuredInterviewPlan` representation so routine logs and assertion failures do not expose sensitive correlations or evidence digests.
- State explicitly that UUID/digest correlation and reference-string inequality do not prove tenant ownership, authoritative relationship validity, or actor identity separation.
