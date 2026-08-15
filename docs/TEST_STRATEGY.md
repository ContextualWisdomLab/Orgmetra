# Test Strategy

## Foundation tests

- Schema naming contract test.
- 3NF relationship test for core HRIS model.
- Bitemporal interval test.
- Candidate-worker append-only linkage test.
- Authorization matrix test for sensitive fields.
- High-impact decision evidence-required test.
- Event envelope schema test.
- Adapter fake-server failure tests.

## Psychometric and validation tests

When Orgmetra invokes psychometric computation, tests must verify result references, versions, and provenance. The numerical kernel remains fast-mlsirm/TEPP unless a future ADR adds Orgmetra-owned compute.

Required evidence for any Orgmetra-owned mathematical compute:

- true-parameter recovery
- bias / MAE / RMSE
- interval coverage
- convergence
- CPU/GPU parity where material
- multilevel and temporal structure where relevant

## UI tests

- Keyboard navigation.
- Screen reader labels.
- Exact-value table for every chart.
- Permission-denied states.
- High-risk confirmation preview.

## Active domain-kernel test evidence

The stacked implementation runs 17 behavioral domain tests plus three repository-contract tests. It proves:

- reversed and ambiguous bitemporal intervals fail closed;
- half-open boundaries behave correctly;
- valid values normalize without silently accepting blanks;
- multiple assignments can sum to one but cannot exceed one during overlap;
- adjacent assignments do not overlap;
- people are validated independently;
- candidate-worker registration is idempotent and cannot relink a candidate to a different person;
- owned production statement and branch coverage are exactly 100%;
- public modules, classes, and functions have docstrings;
- CI actions are commit-pinned and dependencies are hash-locked.
