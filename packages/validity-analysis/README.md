# Orgmetra validity-analysis handoff

This package creates an immutable **selection-validity analysis handoff**. It is the boundary between Orgmetra's authoritative validation-study evidence and numerical work owned by `ContextualWisdomLab/fast-mlsirm`.

## What it does

`build_validation_analysis_handoff(...)` binds one tenant, validation study, Job, predictor snapshot, criterion snapshot, population snapshot, decision policy, analysis plan, requester, reviewer, and the reviewed fast-mlsirm revision `04d0bc21a2a20693bcf16108cd76d394fe844d23`.

The resulting canonical JSON is digest-addressable, contains no raw person-level predictor or criterion values, and remains `not_executed`. Required result evidence is explicit: effect estimate, uncertainty interval, sample size, missingness summary, and convergence diagnostics.

## What it does not do

- It does **not** run statistics.
- It does **not** query fast-mlsirm or any other CWL application's database.
- It does **not** claim that a selection procedure is valid.
- It does **not** interpret adverse impact.
- It does **not** authorize hiring, promotion, termination, compensation, or another employment decision.

The fast-mlsirm repository remains a dedicated-writer dependency. This package records only the immutable revision reviewed for the handoff.

## Host obligations

Before an approved offline validation worker executes the handoff, the Orgmetra host must re-resolve every reference inside `tenant_record_id` and prove that the predictor, criterion, population, and policy evidence belong to the exact validation study and Job. The requester and reviewer must resolve to distinct authoritative actors. A numerical result is scientific evidence for accountable human interpretation, never an autonomous employment decision.

## Verification

Run:

```bash
PYTHONPATH=packages/validity-analysis/src \
python -m pytest -c packages/validity-analysis/pyproject.toml packages/validity-analysis/tests
```

The package gate requires exact 100% owned production statement and branch coverage.
