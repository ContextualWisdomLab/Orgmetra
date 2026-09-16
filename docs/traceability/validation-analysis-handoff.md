# Selection-validity analysis handoff traceability

## Buyer question

Can an organization send one exact, reviewable validation study to its statistical engine without copying raw person-level values into a workflow envelope, silently changing the numerical dependency, or treating model output as an employment decision?

## Active-PR contract

| Concern | Orgmetra evidence | Verification |
|---|---|---|
| Exact study scope | tenant, validation-study, Job, predictor, criterion, population, decision-policy, and analysis-plan references plus digests | namespace/UUID/digest regressions |
| Dependency integrity | immutable fast-mlsirm commit `04d0bc21a2a20693bcf16108cd76d394fe844d23` | malformed and unreviewed revision rejection |
| Privacy minimization | no raw person-level values in canonical handoff or result; result canonicalization accepts only exact governed missingness/convergence runtime types | canonical-payload/redacted-repr regressions plus subclass-injection rejection |
| Human authority | requester/reviewer references must differ, and the host must re-resolve both within the tenant and prove they resolve to distinct authoritative actor identities before execution | direct-construction fail-closed regression plus `test_next_action_requires_resolved_actor_identity_separation` |
| Scientific evidence | effect estimate, uncertainty interval, sample size, internally possible aggregate missingness, convergence diagnostics | immutable required-result-evidence regression plus impossible-missingness rejection |
| Numerical result boundary | handoff digest, pinned fast-mlsirm revision, Rust CPU/GPU backend, precision, finite estimate/interval, aggregate missingness, explicit convergence state | `ValidationAnalysisResult` invariant/canonicalization regressions, exact-runtime-type checks, and oversized-numeric `ValueError` normalization |
| Final point-weight provenance | exact estimand/target/window and case-set digests, source/sampling receipt digests, base-weight evidence, ordered digest-linked adjustments, final weight artifact, append-only correction lineage | `FinalAnalysisWeightReceipt` deterministic/value-minimized regressions plus chain/correction fail-closed tests |
| Nonresponse adjustment evidence | versioned response/disposition receipt, exact adjustment population, controlled method/configuration, explicit ineligible/unknown/unavailable treatment, input/output weight artifacts | `NonresponseAdjustmentReceipt` deterministic/value-minimized tests plus undocumented-treatment/no-op/version rejection |
| Calibration/raking evidence | target population/window, purpose-bound auxiliary projection, authoritative benchmark receipt, algorithm/version, constraints, input/output artifacts, explicit converged/fallback state and immutable fallback rule when used | `CalibrationAdjustmentReceipt` benchmark/termination/fallback regressions |
| Trimming/bounding evidence | versioned trimming/bounding rule, reproducible rule configuration digest, exact affected semantic occurrence set and count, input/output weight artifacts | `test_trimming_bounding_receipt.py` deterministic/value-minimized, no-op, missing-provenance, and typed-kind regressions |
| Typed adjustment congruence | known nonresponse, calibration/raking/post-stratification, and trimming/bounding/winsorization adjustment codes must identify the matching typed receipt family through `evidence_kind` | specialized adjustment evidence-kind regressions |
| Weighted-result congruence | `weighted_design_based` result must bind the exact final point-weight receipt and a separate #406 variance-design receipt; `unweighted` result must bind neither | `test_analysis_weight_result_binding.py` |
| Execution boundary | `not_executed`, `scientific_evidence_only`, read-only pinned foreign dependency | immutable governance regressions |
| Reproducibility | construction-time UTC timestamp snapshots, finite numeric snapshots, canonical RFC 3339 time, canonical JSON, SHA-256 handoff/result/weight/adjustment-receipt digests | mutable timezone/numeric and UTC-boundary regressions plus deterministic serialization/digest tests |
| Decision-record integrity | ADR numbers remain unique repository-wide and any `docs/adr/**` change reaches the consolidated Foundation CI validity regression | ADR uniqueness regression plus Foundation CI workflow-trigger contract regression |
| Quality-evidence freshness | consolidated Foundation CI runs the validity package on every `develop` pull request without a repository path filter, so shared Python/test/clean-checkout configuration cannot silently bypass the package gate | `test_foundation_ci_retriggers_without_path_filter` and `test_foundation_ci_runs_validity_analysis_and_adr_changes`; central required workflows remain separate gates |

## #407 boundary still open

The active branch now makes three adjustment families executable rather than leaving them as opaque digests: nonresponse adjustment evidence is disposition-aware; calibration/raking/post-stratification evidence is bound to an authoritative benchmark, purpose-limited auxiliary projection, constraints, and explicit convergence/fallback state; and trimming/bounding/winsorization evidence is bound to a versioned rule/configuration plus the exact affected occurrence set. This still does not complete #407. Longitudinal/cross-sectional weight eligibility, durable owner-side verification that each adjustment digest resolves to the typed receipt claimed by `evidence_kind`, sensitive auxiliary-variable purpose enforcement, and released auxiliary evidence exchange remain open. `workforce_validation` owns those scientific contracts and their released result; `talent_management` must not compute or reconstruct final analysis weights.

## Maturity

`implemented_on_active_pr`.

Protected `develop` does **not** gain numerical validity computation from this slice. The handoff is execution preparation only. The active package validates the returned numerical/provenance envelope plus the current #407 final-weight/result-binding and typed adjustment-evidence contracts, but protected Orgmetra evidence still requires host re-resolution, durable owner evidence exchange, result-artifact verification, terminal checks, independent review, and accountable human interpretation.