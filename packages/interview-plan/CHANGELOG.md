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
- Replace prose-only activation assurance with executable fail-closed orchestration: the injected host authority must reject failed tenant/relationship/provenance/panel checks, and returned evidence must match the exact tenant, interview-plan reference, plan digest, approving actor, and reviewed approval instant before a receipt can exist.
- Detach caller-owned `approved_at` into one built-in UTC snapshot before chronology or authority work, pass that snapshot to the authority, require the returned verification to carry the same reviewed instant, and write only that immutable snapshot into the receipt.
- Require the exact governed `StructuredInterviewPlan` runtime type before any activation authority work, preventing duck-typed or subclassed plan-shaped objects from bypassing construction invariants and producing approval evidence.
- Pass only creation-bound canonical plan JSON plus its exact SHA-256 digest across `StructuredInterviewActivationAuthority`; the authority no longer receives the caller's live plan object, so temporary change-and-restore (ABA) mutation cannot change the plan revision actually reviewed.
- Derive activation tenant/interview-plan scope from the same canonical plan bytes supplied to the authority and retain the post-authority creation-seal check for any non-restored live-object mutation.
- Make `StructuredInterviewActivationVerification` a runtime-immutable `NamedTuple`, reject subclasses, and unpack its exact tuple once before validation so `object.__setattr__` cannot create mixed authority-evidence revisions between field reads.
- Bind every constructed `StructuredInterviewPlan` to a single-registration process-local creation seal outside plan-writable slots; canonical JSON and SHA-256 export now fail closed if low-level mutation changes the plan, if copied/reconstructed objects lack creation-bound issuance evidence, or if the same live identity attempts to renew its seal through repeated initialization.
- Bind every successfully issued activation receipt to a process-local HMAC seal stored outside receipt-writable slots; canonical JSON and SHA-256 export now fail closed if already-issued receipt fields are rewritten or the creation-bound issuance evidence is unavailable.
- Expand Structured Interview Plan Quality path triggers to cover repository-level Python/test configuration and `.gitignore` inputs that can change test collection, execution, or clean-checkout behavior, while retaining package, dependency-lock, workflow, ADR, doctoring, and traceability triggers.

### Security and privacy

- Reject timestamp/node-bearing UUIDv1 values in package-owned trust references as well as human-readable/value-bearing reference metadata before serialization; tenant UUID generation/privacy policy remains owned by the authoritative HRIS boundary.
- Close plan `reason_code` to `approved_requisition_interview` and activation governance to fixed `structured_interview_activation` / `human_approved_plan_activation` codes.
- Require exact built-in tuple containers for competency/panel reference collections and exact built-in strings for fixed `review_state` / `next_action` evidence before canonicalization, preventing caller-controlled runtime subclasses from passing validation and later switching serialized immutable evidence.
- Normalize approval-time evidence before crossing the authority boundary so caller-controlled mutable `tzinfo` state cannot make one approved action represent different UTC instants before and after review.
- Redact `StructuredInterviewPlan`, `StructuredInterviewActivationVerification`, and `StructuredInterviewActivationReceipt` representations so routine logs and assertion failures do not expose sensitive correlations or evidence digests.
- Treat the process-local plan and activation-receipt seals strictly as in-memory issuance-integrity evidence, not as durable audit stores, portable signatures, cross-process verification keys, or substitutes for the host's immutable audit/outbox contract.
- State explicitly that UUID/digest correlation, reference-string inequality, runtime issuance seals, and the authority protocol do not by themselves prove tenant ownership, authoritative relationship validity, actor identity separation, scientific validity, fairness, or legal compliance.
