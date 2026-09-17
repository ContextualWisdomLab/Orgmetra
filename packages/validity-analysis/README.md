# Orgmetra validity-analysis handoff

This package creates an immutable **selection-validity analysis handoff**, validates the matching numerical result envelope, and preserves executable #407 point-estimation weight lineage. It is the boundary between Orgmetra's authoritative validation-study evidence and numerical work owned by `ContextualWisdomLab/fast-mlsirm`.

## What it does

`build_validation_analysis_handoff(...)` binds one tenant, validation study, Job, predictor snapshot, criterion snapshot, population snapshot, decision policy, analysis plan, requester, reviewer, and the reviewed fast-mlsirm revision `04d0bc21a2a20693bcf16108cd76d394fe844d23`.

The resulting canonical JSON is digest-addressable, contains no raw person-level predictor or criterion values, and remains `not_executed`. Its timestamp is detached to one UTC instant at construction so later timezone-provider changes cannot rewrite the digest. Required result evidence is explicit: effect estimate, uncertainty interval, sample size, missingness summary, and convergence diagnostics.

`FinalAnalysisWeightReceipt` binds a weighted estimand to exact target/window/reference-duration/case-set evidence, source/sampling receipt digests, base-weight evidence, an ordered immutable adjustment chain, the final point-weight artifact digest, and append-only correction lineage. It records only identifiers, versions and digests; it does not store row-level weight values or copy calibration attributes into the validity package.

`WeightEligibilityReceipt` makes cross-sectional versus longitudinal use machine-checkable rather than an opaque weight label. It binds the final weight artifact to one governed scope (`cross_sectional` or `longitudinal`), target population, reference-duration evidence, and eligible-case set. `FinalAnalysisWeightReceipt` fails closed unless those fields match the estimand and the same final point-weight artifact exactly, so a longitudinal weight cannot silently support a cross-sectional estimand or a different reference duration.

Nonresponse and calibration are no longer allowed to hide behind an undifferentiated adjustment digest. `NonresponseAdjustmentReceipt` binds the adjustment to a versioned response/disposition receipt, the exact adjustment population, controlled method/configuration evidence, and explicit treatment codes for ineligible, unknown, and unavailable cases. `CalibrationAdjustmentReceipt` binds the adjustment to a target population/window, **versioned** purpose-bound auxiliary projection identity/digest, exact scientific-use purpose, scientific auxiliary-authority reference, released auxiliary owner-contract reference/version/digest, authorization receipt reference/digest, scientific-use receipt reference/digest and owner-correlatable use instant, plus a separately versioned calibration benchmark receipt with released benchmark owner-contract reference/version/digest and exact benchmark reference instant. It also binds algorithm/version, constraints digest, and explicit `converged` or `fallback_applied` termination evidence. Neither the scientific-use instant nor the benchmark reference instant may be later than receipt construction. A fallback must identify why the primary calibration did not remain authoritative, the immutable fallback rule, and the actual fallback calibration algorithm/version/configuration that produced the output weights; fallback evidence is forbidden on a genuinely converged primary algorithm. A nonconverged calibration cannot masquerade as an accepted calibration receipt. These fields preserve the opaque correlation tuples expected by the canonical Workforce Validation authority boundaries without copying protected auxiliary or benchmark values. The leaf receipt still does not authenticate those coordinates itself: the durable owner service must resolve the released auxiliary and benchmark evidence and prove that the exact projection version and benchmark are authoritative for the scientific use.

Trimming, bounding, and winsorization have a separate provenance family rather than falling back to a generic adjustment label. `TrimmingBoundingAdjustmentReceipt` binds the exact versioned rule, its reproducible configuration digest, the semantic occurrence set and count of cases actually affected, and the input/output weight artifacts. A declared trim/bound transform must change artifact identity. Known trimming/bounding/winsorization adjustment codes fail closed unless `evidence_kind` names this typed receipt family.

`AnalysisWeightAdjustment` records an `evidence_kind` in addition to the evidence digest. Known nonresponse, calibration/raking/post-stratification, and trimming/bounding/winsorization transforms fail closed unless their evidence kind is the corresponding typed receipt. Other adjustment families remain open work rather than being silently treated as equivalent.

`WeightVarianceCompatibilityReceipt` closes the scientific-leaf form of #407 RED #8. It binds one exact `FinalAnalysisWeightReceipt` to the separate #406 variance-design receipt/version/digest and requires the variance side to identify the same analytic-case occurrence set, weight-eligibility receipt, correction sequence, and final point-weight artifact. A replicate or variance construction generated from a different eligibility, correction, case set, or final-weight version therefore cannot be paired with the point estimate merely because both digests are well formed. This receipt is correlation evidence only; #235/#248 remain responsible for resolving the released #406 owner evidence rather than trusting these caller-supplied coordinates as authority.

`ValidationAnalysisResult` accepts only a result linked to the handoff digest and the same reviewed fast-mlsirm revision. It records the Rust CPU/GPU backend, precision, aggregate missingness counts, finite effect and interval values, and explicit convergence or nonconvergence diagnostics. Timestamps and finite numeric values are snapshotted before canonicalization, and the result envelope accepts only the exact governed `MissingnessSummary` and `ConvergenceDiagnostics` runtime types, preventing mutable runtime values or subclass method overrides from adding unreviewed or person-level fields to canonical audit evidence. Missingness counts must be internally possible: complete observations cannot overlap either predictor-missing or criterion-missing observations beyond the declared sample total.

Point-estimation semantics are explicit. `unweighted` results cannot carry weight receipts. `weighted_design_based` results must separately bind the exact `FinalAnalysisWeightReceipt` digest, the variance-design receipt digest that supports the uncertainty method actually used, and the `WeightVarianceCompatibilityReceipt` proving those two evidence paths refer to the same point-weight basis. A replicate/variance evidence reference therefore cannot silently stand in for the final point-estimation weight, or vice versa. The result remains scientific evidence for accountable human interpretation and never becomes an employment decision.

## What it does not do

- It does **not** run statistics.
- It does **not** run or reproduce the fast-mlsirm numerical kernel.
- It does **not** query fast-mlsirm or any other CWL application's database.
- It does **not** claim that a selection procedure is valid.
- It does **not** interpret adverse impact.
- It does **not** authorize hiring, promotion, termination, compensation, or another employment decision.
- It does **not** yet complete #407. Durable owner-side verification that adjustment, point/variance compatibility, auxiliary-authority, and benchmark-authority coordinates resolve to the released typed receipts/contracts they claim; enforcement that the resolved auxiliary projection **version** is authorized for the exact scientific purpose/use receipt/time; and released auxiliary/benchmark/variance evidence exchange remain open work in `workforce_validation`.

The fast-mlsirm repository remains a dedicated-writer dependency. This package records only the immutable revision reviewed for the handoff. Durable Workforce Validation registry/API/persistence remains on the canonical #235/#248 owner path; this package does not create a parallel service.

## Host obligations

Before an approved offline validation worker executes the handoff, the Orgmetra host must re-resolve every reference inside `tenant_record_id` and prove that the predictor, criterion, population, and policy evidence belong to the exact validation study and Job. The requester and reviewer must resolve to distinct authoritative actors. For weighted design-based inference, the host must also verify the final point-weight receipt, its matching cross-sectional/longitudinal weight-eligibility receipt, its upstream source/sampling evidence, each typed adjustment receipt identified by the ordered chain, the calibration auxiliary authority/purpose/released owner contract/authorization/scientific-use tuple including the exact auxiliary projection **version**, the calibration benchmark receipt/version/released benchmark owner contract/reference instant, any fallback reason/rule/actual fallback algorithm-version-configuration tuple, the separately bound #406 variance-design evidence, and the point/variance compatibility receipt against released owner evidence rather than trusting caller-supplied labels or digests. A numerical result is scientific evidence for accountable human interpretation, never an autonomous employment decision.

## Verification

Run:

```bash
PYTHONPATH=packages/validity-analysis/src \
python -m pytest -c packages/validity-analysis/pyproject.toml packages/validity-analysis/tests
```

The package gate requires exact 100% owned production statement and branch coverage.
