# ADR 0027: Govern selection-validity numerical work through an immutable handoff

- Status: Proposed
- Maturity: Active PR only; not protected-branch truth
- Date: 2026-08-21
- Owners: Orgmetra Workforce Validation

## Context

Protected Orgmetra already preserves exact validation-study cases, sealed selection evidence, candidate-to-worker lineage, and Job/cycle/staffing-scoped criterion observations. The remaining boundary is dangerous if left implicit: a statistical worker could receive an underspecified study, silently use a different dependency revision, or turn a model result into an employment decision.

The Uniform Guidelines recognize criterion-related validity evidence as empirical evidence relating a selection procedure to important job-performance elements and require validity studies to be accurate, standardized, documented, and periodically reviewed for currency. SIOP's *Principles for the Validation and Use of Personnel Selection Procedures* likewise treats validation as an evidence-and-inference problem rather than a correlation-only shortcut.

`ContextualWisdomLab/fast-mlsirm` owns numerical psychometric/statistical kernels. Its protected `main` was freshly resolved to commit `04d0bc21a2a20693bcf16108cd76d394fe844d23` on 2026-08-21. Orgmetra must not copy that implementation or write the foreign repository.

## Decision

Orgmetra adds a leaf `orgmetra_validity_analysis` package whose `ValidationAnalysisHandoff`:

- binds the exact tenant, validation study, Job, predictor snapshot, criterion snapshot, population snapshot, decision policy, and analysis plan through opaque references plus SHA-256 evidence digests;
- binds distinct requester and reviewer actor references;
- pins fast-mlsirm to reviewed immutable commit `04d0bc21a2a20693bcf16108cd76d394fe844d23`;
- declares the numerical boundary `read_only_pinned_revision` and the initial strategy `criterion_related`;
- requires downstream result evidence for effect estimate, uncertainty interval, sample size, missingness summary, and convergence diagnostics;
- serializes no raw person-level predictor, criterion, candidate, or worker values;
- remains `not_executed`, `scientific_evidence_only`, and human-review-required;
- produces deterministic canonical JSON and a SHA-256 digest for audit/result correlation.

Both handoff and result envelopes detach exact timezone-aware timestamps to one built-in UTC instant at construction. Result numeric evidence is converted to finite built-in floats before storage, and conversion failures including numeric overflow are normalized to the package's fail-closed `ValueError` contract, so caller-controlled timezone or numeric runtime behavior cannot rewrite canonical evidence after validation or escape normal malformed-result handling.

The same package also validates `ValidationAnalysisResult` envelopes returned by the approved offline worker. A result must link to the handoff digest and the same pinned revision, identify a Rust CPU or GPU backend and precision, provide finite effect and interval values, match its sample size to aggregate missingness counts, reject impossible complete-versus-missing count combinations, and include explicit convergence diagnostics. The canonicalization boundary accepts only the exact governed `MissingnessSummary` and `ConvergenceDiagnostics` runtime types so subclass method overrides cannot add unreviewed or person-level fields to immutable result evidence. A nonconverged result remains typed scientific evidence requiring human review; it cannot be treated as a valid selection procedure or an employment decision.

For #407's weighted design-based inference boundary, the active package adds `FinalAnalysisWeightReceipt`. It binds the exact estimand, target population, analysis window, eligible/analytic case-set digests, #404/#405 source/sampling receipt digests, base-weight derivation evidence, an ordered immutable adjustment chain, the final point-weight artifact digest, construction time, and append-only correction lineage without storing row-level weights. Each adjustment must be contiguous and digest-linked from the previous artifact to the declared final artifact. `ValidationAnalysisResult` explicitly distinguishes `unweighted` from `weighted_design_based`; a weighted result fails closed unless it separately binds both the final analysis-weight receipt digest and the #406 variance-design receipt digest. An unweighted result cannot carry either receipt and thereby masquerade as weighted scientific evidence.

The adjustment chain has typed scientific evidence for three high-risk transform families. `NonresponseAdjustmentReceipt` binds a versioned response/disposition receipt, the exact adjustment population, controlled method/configuration evidence, explicit treatment of ineligible/unknown/unavailable cases, and input/output weight artifacts. `CalibrationAdjustmentReceipt` binds the target population/window, purpose-limited auxiliary projection, authoritative benchmark receipt, algorithm/version, constraints digest, input/output artifacts, and an explicit `converged` or `fallback_applied` termination state. A fallback must identify its immutable fallback-rule reference/digest. A failed/nonconverged calibration cannot be labeled as an accepted calibration receipt. `TrimmingBoundingAdjustmentReceipt` binds a versioned trimming/bounding rule, reproducible rule configuration digest, the semantic occurrence set and count of cases actually affected, and input/output weight artifacts; a declared trim/bound transform cannot be a no-op. Known nonresponse, calibration/raking/post-stratification, and trimming/bounding/winsorization `AnalysisWeightAdjustment` codes also carry an `evidence_kind` and fail closed unless it names the matching typed receipt family.

This executable slice still does not claim #407 complete. Longitudinal/cross-sectional eligibility, durable service/API verification that an adjustment digest resolves to the typed receipt claimed by `evidence_kind`, sensitive auxiliary-variable purpose enforcement, and released auxiliary-owner evidence exchange remain `workforce_validation` scientific truth rather than Talent truth or cross-context SQL reconstruction.

The package does not invoke fast-mlsirm. An approved offline worker is the later execution boundary. Before execution, the Orgmetra host must re-resolve every reference inside the tenant, verify exact study/Job membership and evidence provenance, prove requester/reviewer identities are distinct authoritative actors, and verify typed weight-adjustment receipts rather than trusting caller-supplied evidence labels or digests.

## Consequences

### Positive

- Statistical work cannot silently drift to an unreviewed fast-mlsirm revision.
- A buyer or auditor can identify exactly which governed study evidence a result was supposed to analyze without copying raw worker data into the handoff.
- Aggregate missingness evidence cannot claim all observations are complete while simultaneously reporting predictor- or criterion-missing observations.
- Result canonicalization cannot be extended by an unreviewed subclass to serialize extra decision-like or person-level fields.
- Caller-controlled timestamp and numeric runtime behavior cannot rewrite an accepted canonical digest after construction or turn malformed oversized worker output into an uncaught exception type.
- Weighted design-based results can no longer identify only a sample while omitting which final point-weight evidence and variance-design evidence were actually used.
- The ordered weight transformation chain is independently digest-correlatable without centralizing case-level weights or auxiliary attributes.
- Nonresponse cannot silently drop refusal/unreachable/ineligible/failure dispositions behind one opaque adjustment label.
- Calibration/raking cannot silently float benchmark ownership or hide fallback as successful convergence.
- Trimming/bounding/winsorization cannot silently alter final point weights without an immutable rule/configuration and affected-case receipt.
- Human interpretation remains explicit and separate from numerical output.
- The dedicated-writer boundary remains intact: Orgmetra consumes only a pinned foreign revision/contract boundary and never mutates fast-mlsirm.

### Limitations

- This slice does not execute a statistical model, estimate validity, correct for measurement error/range restriction, evaluate adverse impact, or assert legal compliance.
- Sampling design, estimator choice, missing-data treatment, reliability evidence, multiplicity, transportability, fairness analysis, and model diagnostics must be encoded in the referenced analysis plan and reviewed before execution.
- The current #407 slice validates generic ordered weight provenance, weighted-result binding, disposition-aware nonresponse evidence, benchmark/termination-aware calibration evidence, and trimming/bounding rule provenance; it does not yet make longitudinal eligibility, durable typed-receipt resolution, or sensitive auxiliary-owner enforcement fully executable.
- The generic result envelope does not invent an estimator-specific minimum complete-case count. Whether a converged estimator is identified under a particular missing-data design belongs to the reviewed analysis plan and numerical-worker contract; Orgmetra fails closed on impossible aggregate counts without silently replacing that foreign scientific contract with complete-case analysis.
- The package validates the result envelope, but a future execution adapter must still re-resolve the handoff references, verify the result provenance artifact, resolve typed adjustment digests to released owner evidence, and attach evidence only after accountable human review.

## Verification

The package regression suite starts RED when the public handoff contract is absent and covers canonical operational tenant UUIDs, opaque UUIDv4 references, exact evidence digests, distinct human actors, exact dependency pinning, timezone-aware event time, immutable governance constants, value minimization, deterministic canonicalization, SHA-256 correlation, impossible aggregate missingness rejection, oversized numeric conversion rejection, exact governed aggregate-evidence runtime types, and 100% owned production statement/branch coverage. #407 adds RED/GREEN coverage for deterministic value-minimized final-weight receipts, exact sampling-receipt binding, contiguous transformation lineage, append-only correction linkage, fail-closed weighted-result binding to separate point-weight and variance-design receipts, explicit nonresponse disposition treatment, calibration benchmark/constraint/termination provenance, fallback-rule disclosure, trimming/bounding rule/configuration and affected-case provenance, no-op trim/bound rejection, and typed adjustment-evidence matching. The repository-wide ADR numbering regression also fails closed if integration reuses an existing decision number, and the validity quality workflow contract requires any `docs/adr/**` change to execute that regression.

## References

See `docs/doctoring/validation-analysis-handoff-references.md`.