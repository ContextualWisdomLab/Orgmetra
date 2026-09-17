# Changelog

## 0.1.0 - Unreleased

- Add a governed, value-minimized criterion-related validity analysis handoff.
- Pin the reviewed read-only fast-mlsirm dependency revision.
- Require separate requester/reviewer references and authoritative tenant-scoped re-resolution proving they resolve to distinct actor identities before execution.
- Require deterministic canonical evidence and 100% owned production statement/branch coverage.
- Validate a digest-linked Rust CPU/GPU result envelope with finite estimates, aggregate missingness, and explicit convergence or nonconvergence diagnostics.
- Reject impossible aggregate missingness where complete observations overlap either predictor-missing or criterion-missing counts beyond the sample total.
- Require exact governed missingness/convergence runtime types so subclass method overrides cannot inject unreviewed or person-level fields into canonical result evidence.
- Freeze exact UTC timestamps and finite numeric values at construction, and reject runtime-type forgery before canonical evidence serialization.
- Add a deterministic, row-value-minimized `FinalAnalysisWeightReceipt` that binds an exact estimand to source/sampling evidence, base-weight provenance, an ordered digest-linked adjustment chain, the final point-weight artifact, and append-only correction lineage.
- Add `WeightEligibilityReceipt` and fail closed unless cross-sectional/longitudinal scope, target population, reference duration, eligible case set, and final point-weight artifact match the estimand-side final-weight receipt exactly.
- Distinguish unweighted from weighted design-based results and fail closed unless a weighted result separately binds the exact final analysis-weight receipt and variance-design receipt used.
- Add `WeightVarianceCompatibilityReceipt` so variance evidence must correlate to the exact final point-weight receipt, analytic-case occurrence set, weight-eligibility receipt, correction sequence, and final-weight artifact before a weighted result can be emitted. The receipt is correlation evidence, not self-authenticating #406 owner authority.
- Require `ValidationAnalysisResult` to bind the compatibility receipt in addition to the point-weight and variance-design digests; unweighted results cannot carry compatibility evidence.
- Add typed `NonresponseAdjustmentReceipt` evidence that binds the exact versioned response/disposition receipt reference/version/digest, adjustment population, controlled method/configuration, explicit ineligible/unknown/unavailable treatment, and input/output weight artifacts; add typed `CalibrationAdjustmentReceipt` evidence bound to purpose-limited auxiliary projections, exact scientific-use purpose, scientific auxiliary-authority reference, released owner-contract reference/version/digest, authorization receipt reference/digest, scientific-use receipt reference/digest/use time, authoritative benchmark receipts, constraints, and explicit convergence/fallback state; the use time cannot be later than receipt construction.
- Add typed `TrimmingBoundingAdjustmentReceipt` evidence that binds a versioned rule/configuration, exact affected semantic occurrence set and count, and input/output weight artifacts; known trimming/bounding/winsorization adjustments must name that evidence family.
- Require known nonresponse, calibration/raking/post-stratification, and trimming/bounding/winsorization adjustment codes to identify the matching typed evidence kind rather than collapse into a generic opaque adjustment digest.
- Keep durable owner-side typed-receipt, point/variance compatibility, and auxiliary-authority resolution plus released auxiliary/variance evidence exchange explicitly incomplete under #407; the scientific leaf preserves exact correlation coordinates but does not self-authenticate them.
- Make `Validity Analysis Handoff Quality` retrigger on shared repository Python/test/clean-checkout configuration, with an executable regression preventing stale package-quality evidence after shared tooling changes.
