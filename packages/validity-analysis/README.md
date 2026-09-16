# Orgmetra validity-analysis handoff

This package creates an immutable **selection-validity analysis handoff**, validates the matching numerical result envelope, and preserves the first executable #407 point-estimation weight lineage contract. It is the boundary between Orgmetra's authoritative validation-study evidence and numerical work owned by `ContextualWisdomLab/fast-mlsirm`.

## What it does

`build_validation_analysis_handoff(...)` binds one tenant, validation study, Job, predictor snapshot, criterion snapshot, population snapshot, decision policy, analysis plan, requester, reviewer, and the reviewed fast-mlsirm revision `04d0bc21a2a20693bcf16108cd76d394fe844d23`.

The resulting canonical JSON is digest-addressable, contains no raw person-level predictor or criterion values, and remains `not_executed`. Its timestamp is detached to one UTC instant at construction so later timezone-provider changes cannot rewrite the digest. Required result evidence is explicit: effect estimate, uncertainty interval, sample size, missingness summary, and convergence diagnostics.

`FinalAnalysisWeightReceipt` binds a weighted estimand to exact target/window/case-set evidence, source/sampling receipt digests, base-weight evidence, an ordered immutable adjustment chain, the final point-weight artifact digest, and append-only correction lineage. It records only identifiers, versions and digests; it does not store row-level weight values or copy calibration attributes into the validity package.

`ValidationAnalysisResult` accepts only a result linked to the handoff digest and the same reviewed fast-mlsirm revision. It records the Rust CPU/GPU backend, precision, aggregate missingness counts, finite effect and interval values, and explicit convergence or nonconvergence diagnostics. Timestamps and finite numeric values are snapshotted before canonicalization, and the result envelope accepts only the exact governed `MissingnessSummary` and `ConvergenceDiagnostics` runtime types, preventing mutable runtime values or subclass method overrides from adding unreviewed or person-level fields to canonical audit evidence. Missingness counts must be internally possible: complete observations cannot overlap either predictor-missing or criterion-missing observations beyond the declared sample total.

Point-estimation semantics are explicit. `unweighted` results cannot carry weight receipts. `weighted_design_based` results must separately bind the exact `FinalAnalysisWeightReceipt` digest and the variance-design receipt digest that supports the uncertainty method actually used. A replicate/variance evidence reference therefore cannot silently stand in for the final point-estimation weight, or vice versa. The result remains scientific evidence for accountable human interpretation and never becomes an employment decision.

## What it does not do

- It does **not** run statistics.
- It does **not** run or reproduce the fast-mlsirm numerical kernel.
- It does **not** query fast-mlsirm or any other CWL application's database.
- It does **not** claim that a selection procedure is valid.
- It does **not** interpret adverse impact.
- It does **not** authorize hiring, promotion, termination, compensation, or another employment decision.
- It does **not** yet implement all #407 adjustment-specific contracts. Nonresponse-disposition evidence, calibration/raking benchmark-owner receipts and constraints, trimming/bounding rules, longitudinal eligibility, convergence/fallback semantics, and sensitive auxiliary-variable purpose binding remain explicit open work in `workforce_validation`.

The fast-mlsirm repository remains a dedicated-writer dependency. This package records only the immutable revision reviewed for the handoff. Durable Workforce Validation registry/API/persistence remains on the canonical #235/#248 owner path; this package does not create a parallel service.

## Host obligations

Before an approved offline validation worker executes the handoff, the Orgmetra host must re-resolve every reference inside `tenant_record_id` and prove that the predictor, criterion, population, and policy evidence belong to the exact validation study and Job. The requester and reviewer must resolve to distinct authoritative actors. For weighted design-based inference, the host must also verify the final point-weight receipt, its upstream source/sampling evidence, and the separately bound variance-design evidence rather than trusting caller-supplied labels. A numerical result is scientific evidence for accountable human interpretation, never an autonomous employment decision.

## Verification

Run:

```bash
PYTHONPATH=packages/validity-analysis/src \
python -m pytest -c packages/validity-analysis/pyproject.toml packages/validity-analysis/tests
```

The package gate requires exact 100% owned production statement and branch coverage.
