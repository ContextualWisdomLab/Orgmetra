# Changelog

## 0.1.0 - Unreleased

### Added

- Candidate-neutral `StructuredInterviewPlan` binding an approved requisition and Job to exact job-analysis, question-set, question-to-competency mapping, rating-anchor, competency, and interviewer-panel evidence.
- Fail-closed direct-construction validation, deterministic canonical JSON/SHA-256 audit correlation, explicit human approval state, and 100% owned statement/branch regression coverage.
- Bounded positive `evidence_version` in canonical evidence so materially revised plans have explicit immutable revision identity.
- Executable `StructuredInterviewActivationAuthority` / `activate_structured_interview_plan(...)` boundary that requires exact-scope authoritative verification before emitting any approval evidence.
- Value-minimized `StructuredInterviewActivationReceipt` binding the exact plan digest, accountable approving actor, authority-verification reference/digest, fixed purpose/reason, evidence version, precision-preserving approval time, mandatory human confirmation, and fixed `approved_for_use` state.

### Changed

- Require a separately identified and SHA-256-bound question-to-competency mapping artifact so question count alone cannot be treated as proof that every governed competency is assessed.
- Revalidate evidence-version changes through direct construction and `dataclasses.replace(...)`; changing the version changes canonical SHA-256 correlation.
- Keep package-owned trust-bearing reference suffixes canonical non-sentinel UUIDv4, while `tenant_record_id` follows Orgmetra's authoritative canonical non-sentinel operational UUID contract so valid core tenant identities are not rejected by this leaf package.
- Replace prose-only activation assurance with executable fail-closed orchestration: the injected host authority must reject failed tenant/relationship/provenance/panel checks, and returned evidence must match the exact tenant, interview-plan reference, plan digest, and approving actor before a receipt can exist.
- Validate `approved_at` before authoritative activation work and reject approval evidence that predates the reviewed plan's `generated_at`, preventing impossible audit chronology from reaching the host authority.

### Security and privacy

- Reject timestamp/node-bearing UUIDv1 values in package-owned trust references as well as human-readable/value-bearing reference metadata before serialization; tenant UUID generation/privacy policy remains owned by the authoritative HRIS boundary.
- Close plan `reason_code` to `approved_requisition_interview` and activation governance to fixed `structured_interview_activation` / `human_approved_plan_activation` codes.
- Redact both `StructuredInterviewPlan` and `StructuredInterviewActivationReceipt` representations so routine logs and assertion failures do not expose sensitive correlations or evidence digests.
- State explicitly that UUID/digest correlation, reference-string inequality, and the authority protocol do not by themselves prove tenant ownership, authoritative relationship validity, actor identity separation, scientific validity, fairness, or legal compliance.
