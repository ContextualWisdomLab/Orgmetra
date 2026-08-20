# ADR 0025: Govern selection-validity numerical work through an immutable handoff

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

The package does not invoke fast-mlsirm. An approved offline worker is the later execution boundary. Before execution, the Orgmetra host must re-resolve every reference inside the tenant, verify exact study/Job membership and evidence provenance, and prove requester/reviewer identities are distinct authoritative actors.

## Consequences

### Positive

- Statistical work cannot silently drift to an unreviewed fast-mlsirm revision.
- A buyer or auditor can identify exactly which governed study evidence a result was supposed to analyze without copying raw worker data into the handoff.
- Human interpretation remains explicit and separate from numerical output.
- The dedicated-writer boundary remains intact: Orgmetra consumes only a pinned foreign revision/contract boundary and never mutates fast-mlsirm.

### Limitations

- This slice does not execute a statistical model, estimate validity, correct for measurement error/range restriction, evaluate adverse impact, or assert legal compliance.
- Sampling design, estimator choice, missing-data treatment, reliability evidence, multiplicity, transportability, fairness analysis, and model diagnostics must be encoded in the referenced analysis plan and reviewed before execution.
- A future execution/result adapter must validate the returned model/provenance schema before any result is attached to an Orgmetra study.

## Verification

The package regression suite starts RED when the public handoff contract is absent and covers canonical operational tenant UUIDs, opaque UUIDv4 references, exact evidence digests, distinct human actors, exact dependency pinning, timezone-aware event time, immutable governance constants, value minimization, deterministic canonicalization, SHA-256 correlation, and 100% owned production statement/branch coverage.

## References

See `docs/doctoring/validation-analysis-handoff-references.md`.
