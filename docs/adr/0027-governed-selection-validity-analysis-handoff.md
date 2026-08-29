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

Both handoff and result envelopes detach exact timezone-aware timestamps to one built-in UTC instant at construction. Result numeric evidence is converted to finite built-in floats before storage, so caller-controlled timezone or numeric runtime behavior cannot rewrite canonical evidence after validation.

The same package also validates `ValidationAnalysisResult` envelopes returned by the approved offline worker. A result must link to the handoff digest and the same pinned revision, identify a Rust CPU or GPU backend and precision, provide finite effect and interval values, match its sample size to aggregate missingness counts, reject impossible complete-versus-missing count combinations, and include explicit convergence diagnostics. The canonicalization boundary accepts only the exact governed `MissingnessSummary` and `ConvergenceDiagnostics` runtime types so subclass method overrides cannot add unreviewed or person-level fields to immutable result evidence. A nonconverged result remains typed scientific evidence requiring human review; it cannot be treated as a valid selection procedure or an employment decision.

The package does not invoke fast-mlsirm. An approved offline worker is the later execution boundary. Before execution, the Orgmetra host must re-resolve every reference inside the tenant, verify exact study/Job membership and evidence provenance, and prove requester/reviewer identities are distinct authoritative actors.

## Consequences

### Positive

- Statistical work cannot silently drift to an unreviewed fast-mlsirm revision.
- A buyer or auditor can identify exactly which governed study evidence a result was supposed to analyze without copying raw worker data into the handoff.
- Aggregate missingness evidence cannot claim all observations are complete while simultaneously reporting predictor- or criterion-missing observations.
- Result canonicalization cannot be extended by an unreviewed subclass to serialize extra decision-like or person-level fields.
- Caller-controlled timestamp and numeric runtime behavior cannot rewrite an accepted canonical digest after construction.
- Human interpretation remains explicit and separate from numerical output.
- The dedicated-writer boundary remains intact: Orgmetra consumes only a pinned foreign revision/contract boundary and never mutates fast-mlsirm.

### Limitations

- This slice does not execute a statistical model, estimate validity, correct for measurement error/range restriction, evaluate adverse impact, or assert legal compliance.
- Sampling design, estimator choice, missing-data treatment, reliability evidence, multiplicity, transportability, fairness analysis, and model diagnostics must be encoded in the referenced analysis plan and reviewed before execution.
- The package validates the result envelope, but a future execution adapter must still re-resolve the handoff references, verify the result provenance artifact, and attach evidence only after accountable human review.

## Verification

The package regression suite starts RED when the public handoff contract is absent and covers canonical operational tenant UUIDs, opaque UUIDv4 references, exact evidence digests, distinct human actors, exact dependency pinning, timezone-aware event time, immutable governance constants, value minimization, deterministic canonicalization, SHA-256 correlation, impossible aggregate missingness rejection, exact governed aggregate-evidence runtime types, and 100% owned production statement/branch coverage. The repository-wide ADR numbering regression also fails closed if integration reuses an existing decision number.

## References

See `docs/doctoring/validation-analysis-handoff-references.md`.
