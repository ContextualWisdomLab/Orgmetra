# Rust-First Validity Execution Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a governed, reproducible adapter boundary that records real pinned fast-mlsirm Rust CPU recovery evidence without misrepresenting recovery metrics as criterion-related validity estimates.

**Architecture:** Orgmetra owns only immutable request and recovery-evidence contracts. A small evidence runner invokes the separately checked-out fast-mlsirm revision through its existing public API, verifies the exact Git revision, and converts only aggregate worker output into a redacted receipt. Cross-sectional and nested multilevel designs are runnable; multiple-membership and longitudinal designs remain explicit contract-only capabilities until a reviewed estimator exists.

**Tech Stack:** Python 3.12, stdlib dataclasses/json/subprocess, uv, pytest-cov, pinned fast-mlsirm Rust backend.

**Spec:** `docs/adr/0027-governed-selection-validity-analysis-handoff.md` and the user-provided Orgmetra execution requirements.

## Global Constraints

- Keep `ContextualWisdomLab/fast-mlsirm` a read-only dedicated-writer dependency at revision `04d0bc21a2a20693bcf16108cd76d394fe844d23`.
- Never map simulation recovery RMSE to `ValidationAnalysisResult.effect_estimate` or claim criterion-related validity from this lane.
- Do not carry raw person-level observations, credentials, or foreign application database access across the boundary.
- Use Rust CPU execution for the runnable evidence path; GPU evidence is recorded only when an actual GPU run succeeds, and no GPU parity claim is made without paired measurements.
- Preserve 100% owned statement and branch coverage for the package.

---

### Task 1: Add fail-closed execution and design contracts

**Files:**
- Create: `packages/validity-analysis/src/orgmetra_validity_analysis/execution.py`
- Create: `packages/validity-analysis/src/orgmetra_validity_analysis/recovery_runner.py`
- Modify: `packages/validity-analysis/src/orgmetra_validity_analysis/__init__.py`
- Test: `packages/validity-analysis/tests/test_execution.py`
- Test: `packages/validity-analysis/tests/test_recovery_runner.py`

**Interfaces:**
- `RustExecutionRequest` binds an opaque execution reference, handoff digest, dataset digest, exact kernel revision, design code, dimensions, seed, backend, and device.
- `RustRecoveryEvidence` stores aggregate Rust fit/recovery output and remains `scientific_evidence_only`.
- `build_rust_recovery_evidence(request, worker_output, completed_at)` validates a JSON-like worker response and binds it to `request.sha256_digest()`.
- `RustExecutionRequest.runnable` is true only for `cross_sectional` and `nested_multilevel`; `multiple_membership` and `longitudinal` are contract-only and raise `UnsupportedExecutionDesign` when execution is requested.

- [x] **Step 1: Write tests for deterministic redacted request/evidence JSON, exact revision pinning, design capability guards, malformed worker output, and request/evidence digest linkage.**
- [x] **Step 2: Run `env -u PYTHONPATH uv run --project packages/validity-analysis --extra test pytest packages/validity-analysis/tests/test_execution.py`; observe the expected RED failure before the new module exists.**
- [x] **Step 3: Implement the two frozen dataclasses and one builder with standard-library validation only; do not import fast-mlsirm into the package.**
- [x] **Step 4: Export only the reviewed public symbols and rerun the focused test until it is GREEN.**
- [x] **Step 5: Run the complete package gate and confirm 100% statement/branch coverage.**

### Task 2: Add the real pinned fast-mlsirm recovery evidence runner

**Files:**
- Create: `packages/validity-analysis/scripts/run_fast_mlsirm_recovery_evidence.py`
- Modify: `packages/validity-analysis/README.md`
- Modify: `packages/validity-analysis/CHANGELOG.md`
- Test: `packages/validity-analysis/tests/test_execution_script_contract.py`

**Interfaces:**
- CLI: `uv run --project packages/validity-analysis --extra test python packages/validity-analysis/scripts/run_fast_mlsirm_recovery_evidence.py --fast-mlsirm-path /private/tmp/orgmetra-fast-mlsirm-04d0 --design-code nested_multilevel`.
- The runner verifies a clean `git -C <path>` checkout and exact `HEAD`, invokes `uv run --frozen --no-editable --project <path> python -c ...` with external uv/Cargo build directories and a 180-second timeout, requests `backend="rust"` and `rust_device="cpu"`, uses a deterministic seed and small bounded sample, and emits only canonical aggregate evidence JSON.
- The worker uses `cluster_id` for nested multilevel evidence and records `max_iter_reached` explicitly when the bounded smoke run does not converge.
- The runner does not invoke unsupported multiple-membership or longitudinal designs and exits with an actionable non-zero error.

- [x] **Step 1: Write a contract test that checks the CLI exposes the exact revision/path/design arguments and rejects an unpinned checkout without running model code.**
- [x] **Step 2: Run the focused script-contract test with `--no-cov` and confirm the two contract tests pass.**
- [x] **Step 3: Implement the bounded subprocess runner with no shell interpolation of untrusted path data, exact clean-revision verification before and after execution, minimal environment forwarding, external uv/Cargo build directories, an explicit timeout, and JSON-only stdout.**
- [x] **Step 4: Run the real runner against a clean sparse worktree of revision `04d0bc21a2a20693bcf16108cd76d394fe844d23` and preserve the observed output as a local verification artifact, distinguishing bounded smoke evidence from estimator acceptance.**
- [x] **Step 5: Document the command, observed Rust CPU evidence, unsupported design boundaries, and the unrun GPU parity requirement.**

### Task 3: Repository and handoff verification

**Files:**
- Modify: `docs/adr/0027-governed-selection-validity-analysis-handoff.md`
- No change: `docs/product-technical-gap-baseline.md` is not present on the PR #57 stacked base; the active gap baseline remains tracked by PR #53.
- Modify: `manifest.json`

- [x] **Step 1: Run the package gate, repository validator, root npm validation, `git diff --check`, and CodeGraph status from the isolated worktree.**
- [ ] **Step 2: Re-check the exact branch head and PR #58 state without bypassing protection or manufacturing approval.**
- [ ] **Step 3: Request independent review evidence when the hosted review path is available; keep the PR unmerged while checks/review are queued or missing.**
- [x] **Step 4: Update the active plan and handoff notes with observed, inferred, and still-open evidence separately.**

## Self-review checklist

- Recovery evidence is never constructively accepted as a validity result.
- The external repository is read-only and pinned by exact commit.
- Unsupported temporal and multiple-membership execution fails closed instead of flattening the design.
- No GPU parity or protected-branch truth is claimed without fresh runtime evidence.
- Every new production branch has a package test and the package remains at 100% statement/branch coverage.
