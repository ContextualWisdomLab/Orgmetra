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

The stacked implementation runs the `orgmetra-domain` unittest suite plus repository-contract tests. After the recorded-time and identity-scope repair it proves:

- reversed and ambiguous bitemporal intervals fail closed;
- half-open boundaries hide a row at exact `recorded_to`;
- a `+09:00` knowledge time matches the equivalent UTC recorded instant;
- a legal name change is effective-dated, not only retroactively corrected;
- mixed identities resolve per person instead of raising one tenant-wide ambiguity;
- valid values normalize without silently accepting blanks;
- employment and position anchors carry no mutable status;
- multiple assignments can sum to one but cannot exceed one during overlap;
- a closed recorded assignment interval does not inflate current FTE;
- the A/A'/B retroactive correction triple is accepted as-of the correction instant;
- assignment ratios that cannot persist as `numeric(5,4)` fail closed;
- an assignment must name a covering employment for the same person;
- concurrent employments keep assignments on the named relationship;
- job-share at 0.5 + 0.5 is accepted and two full assignments to one position are rejected;
- adjacent assignments do not overlap;
- people are validated independently;
- a visible organization cycle A→B→A fails closed;
- candidate-worker registration is idempotent and cannot relink a candidate to a different person;
- relink and allocation errors omit UUIDs, dates, and ratios;
- `__post_init__` public methods require beginner-readable docstrings;
- owned production statement and branch coverage are exactly 100%;
- CI actions are commit-pinned and dependencies are hash-locked;
- the quality script builds the wheel, checks `py.typed`, and smoke-imports the installed artifact.
