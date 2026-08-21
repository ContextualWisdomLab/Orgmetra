# Orgmetra validity-analysis handoff

This package creates an immutable **selection-validity analysis handoff**, validates the matching numerical result envelope, and records a separate pinned-kernel recovery-evidence receipt. It is the boundary between Orgmetra's authoritative validation-study evidence and numerical work owned by `ContextualWisdomLab/fast-mlsirm`.

## What it does

`build_validation_analysis_handoff(...)` binds one tenant, validation study, Job, predictor snapshot, criterion snapshot, population snapshot, decision policy, analysis plan, requester, reviewer, and the reviewed fast-mlsirm revision `04d0bc21a2a20693bcf16108cd76d394fe844d23`.

The resulting canonical JSON is digest-addressable, contains no raw person-level predictor or criterion values, and remains `not_executed`. Required result evidence is explicit: effect estimate, uncertainty interval, sample size, missingness summary, and convergence diagnostics.

`ValidationAnalysisResult` accepts only a result linked to the handoff digest and the same reviewed fast-mlsirm revision. It records the Rust CPU/GPU backend, precision, aggregate missingness counts, finite effect and interval values, and explicit convergence or nonconvergence diagnostics. Missingness counts must be internally possible: complete observations cannot overlap either predictor-missing or criterion-missing observations beyond the declared sample total. The result envelope accepts only the exact governed `MissingnessSummary` and `ConvergenceDiagnostics` runtime types, preventing subclass method overrides from adding unreviewed or person-level fields to canonical audit evidence. It never promotes a result to an employment decision; human review remains mandatory.

`RustExecutionRequest` makes cross-sectional, nested multilevel, multiple-membership, and longitudinal design metadata explicit. Only cross-sectional and nested multilevel requests are currently runnable. `RustRecoveryEvidence` records aggregate simulation-recovery metrics from a bounded worker run; it is not a criterion-related validity estimate and cannot be converted into `ValidationAnalysisResult.effect_estimate`.

The read-only evidence runner verifies the exact pinned checkout before starting the foreign worker:

```bash
uv run --project packages/validity-analysis --extra test \
  python packages/validity-analysis/scripts/run_fast_mlsirm_recovery_evidence.py \
  --fast-mlsirm-path /private/tmp/orgmetra-fast-mlsirm-04d0 \
  --handoff-digest <sha256> --design-code nested_multilevel \
  --rust-device cpu --worker-count 4 --timeout-seconds 180
```

The bounded run uses `backend="rust"`, a deterministic seed, a small synthetic matrix, `RAYON_NUM_THREADS=4`, and a 180-second subprocess timeout. It emits only canonical aggregate JSON. A `max_iter_reached` result remains explicit recovery evidence and is not estimator acceptance.

## What it does not do

- It does **not** estimate criterion-related validity or run an approved offline validity worker.
- The core package does **not** import fast-mlsirm; the optional evidence script invokes only the pinned public API for bounded recovery evidence.
- It does **not** query fast-mlsirm or any other CWL application's database.
- It does **not** estimate multiple-membership or longitudinal designs; those contracts fail closed.
- It does **not** claim GPU availability or GPU/CPU numerical parity without paired runtime measurements.
- It does **not** claim that a selection procedure is valid.
- It does **not** interpret adverse impact.
- It does **not** authorize hiring, promotion, termination, compensation, or another employment decision.

The fast-mlsirm repository remains a dedicated-writer dependency. The runner reads a separately checked-out exact revision and never writes that repository.

## Host obligations

Before an approved offline validation worker executes the handoff, the Orgmetra host must re-resolve every reference inside `tenant_record_id` and prove that the predictor, criterion, population, and policy evidence belong to the exact validation study and Job. The requester and reviewer must resolve to distinct authoritative actors. A numerical result is scientific evidence for accountable human interpretation, never an autonomous employment decision.

## Verification

Run:

```bash
uv run --project packages/validity-analysis --extra test \
  pytest packages/validity-analysis/tests
```

The package gate requires exact 100% owned production statement and branch coverage.
