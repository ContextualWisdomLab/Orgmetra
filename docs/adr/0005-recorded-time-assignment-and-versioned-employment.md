# ADR 0005: Recorded-time assignment integrity and versioned employment/position

## Status

Proposed in the active domain-kernel implementation PR.

## Context

PR #3's first kernel could answer “what name did we know on this date?” and still reject a legal assignment correction. `validate_assignment_portfolio()` summed every row by effective date only, so a closed recorded interval still counted toward FTE. The same head leaked candidate and person identifiers on relink, treated two people as one ambiguous fact, and used one identifier as both employment/position identity and version identity.

Those gaps contradict the bitemporal contract in ADR 0003 and the identity-versus-version split already accepted for organization and job. They also recreate the atomistic fallacy: a person can hold more than one employment and more than one assignment, and a position can be job-shared, so allocation must be evaluated per person and per position at a knowledge-time coordinate (Browne et al., 2001; Raudenbush & Bryk, 2002).

SQL period predicates and asserted-versioning practice require both valid time and transaction time to reconstruct what was known (International Organization for Standardization, 2023; Jensen & Snodgrass, 1999).

## Decision

1. `validate_assignment_portfolio()` requires timezone-aware `known_at` and counts only rows visible at that instant. `validate_assignment_portfolio_history()` repeats the check at every recorded endpoint before a write.
2. `AssignmentRecord` names the durable `employment_record_id`. Coverage validation requires the visible employment version to contain the assignment's effective interval.
3. Employment and position follow the organization/job pattern: durable anchors plus `EmploymentVersionRecord` / `PositionVersionRecord`.
4. Historical resolution is identity-scoped. `resolve_bitemporal_facts_by_identity()` fails closed only when one identity has two visible versions. The single-fact helper rejects mixed-identity collections.
5. Adapter-crossing errors stay generic. Relink and allocation messages contain no UUID, date, or ratio.
6. `allocation_ratio` must persist as `numeric(5,4)`: finite, `(0, 1]`, at most four decimal places.
7. A visible organization parent cycle such as A→B→A fails closed.

Persistence adapters must mirror these invariants transactionally after the foundation baseline merges. The vendored stacked schema on this branch remains a predecessor snapshot and is not the accepted persistence shape.

## Consequences

- HR can correct FTE without the kernel treating superseded rows as current staff.
- Rehire and dual employment can say which relationship an assignment belongs to.
- A retroactive employment-status or position-status correction does not look like a second employment or a new seat.
- Callers must pass `known_at` and `identity_of`. That is a breaking change for the 0.1 draft API.
- Downstream persistence (PR #5) must add `employment_record_id`, version tables, and recorded-time gist exclusions before it can embed this kernel.

## Acceptance evidence

- Buyer-visible RED/GREEN cases for the A/A'/B correction triple, mixed-identity resolution, legal name change, `+09:00` knowledge time, covering employment, job-share, same-position over-occupancy, and organization cycle.
- Exact 100% production statement and branch coverage.
- Public docstring gate including `__post_init__`.
- Citations recorded in `docs/doctoring/REFERENCES.md`.
