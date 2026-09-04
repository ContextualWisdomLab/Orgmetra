# ADR 0011: Workforce composition is a bitemporal aggregate evidence boundary

## Status

Accepted on active PR #33 only. This document is not protected-`develop` product truth until the owning PR integrates.

## Context

Orgmetra already owns tenant-scoped bitemporal Employment and Assignment truth, but buyers also need defensible workforce-composition reporting. A reporting layer that simply counts current rows would lose both the business-time question (what workforce state was effective on a date) and the system-time question (what Orgmetra knew at a historical cutoff). A reporting layer that copies worker rows downstream would also create another PII-bearing system of record.

ISO 30414:2025, the second edition of the international human-capital reporting and disclosure standard, identifies workforce composition as one of its core human-capital reporting areas. Orgmetra uses the public standard metadata and scope as design traceability only; this ADR neither reproduces proprietary standard content nor claims certification.

## Decision

Orgmetra will expose a pure `WorkforceCompositionSnapshot` derived from authoritative HRIS facts at an explicit `(tenant_record_id, effective_on, known_at)` coordinate.

- `active` and `leave` employments are reportable because they are the same statuses allowed to carry assignments in the protected HRIS kernel.
- Headcount is the number of distinct people with reportable visible employment. Valid concurrent employments therefore do not double-count one person.
- Employment count preserves the number of visible reportable employment relationships.
- Before aggregation, the snapshot reuses the HRIS employment-concurrency invariant at the report coordinate. Two overlapping `exclusive` employments or an unknown concurrency code fail closed instead of being normalized into plausible headcount.
- Staffed assignment count and staffed FTE are computed from visible assignments after reusing the existing assignment-to-employment coverage, per-employment allocation, and position-seat capacity integrity rules.
- One overfilled Position seat therefore remains a data-integrity failure even when the aggregate FTE total itself looks plausible.
- Unassigned-person count surfaces a buyer-actionable staffing gap without serializing row-level worker identity.
- Status counts are aggregate employment evidence, sorted deterministically.
- Two visible versions of one Employment or Assignment identity fail closed. Invalid assignment coverage or over-allocation remains a data-integrity error rather than becoming a plausible metric.
- The canonical JSON contains the opaque tenant identifier, report coordinates, aggregate metrics, and schema version only. It excludes person, employment, assignment, and position identifiers and all human-readable PII.
- SHA-256 addresses the exact canonical UTF-8 representation so a caller can correlate a report with immutable audit evidence without copying source rows.
- This contract is descriptive. It must not recommend or execute hiring, promotion, termination, compensation, scheduling, or other high-impact employment decisions.

## Consequences

### Positive

- Buyers can reconstruct workforce composition for both business time and knowledge time instead of receiving an ahistorical current-row count.
- Concurrent employment is represented without inflating person headcount, while employment and FTE measures retain portfolio shape.
- Invalid exclusive-employment overlap or overfilled Position capacity remains a visible data-integrity failure rather than silently becoming a report.
- Existing HRIS integrity rules remain the single source of truth for employment concurrency, assignment validity, and position capacity.
- Aggregate serialization minimizes PII and avoids a shadow worker database.
- Deterministic evidence can be bound to governed audit/report delivery later.

### Costs and limitations

- This slice does not implement a dashboard, export endpoint, report authorization policy, persistence table, forecasting model, diversity inference, or automated workforce action.
- Whether a particular metric or disclosure is required for an organization's ISO 30414 program depends on the licensed standard and the organization's reporting context; Orgmetra does not infer compliance from this kernel contract.
- Rich organizational breakdowns require a later bounded slice that binds assignments to effective organization/job dimensions without leaking protected or low-cell-count data.

## Verification

`packages/hris-kernel/tests/test_workforce_composition.py`, `packages/hris-kernel/tests/test_workforce_composition_boundaries.py`, and `packages/hris-kernel/tests/test_workforce_position_capacity.py` require tenant isolation, concurrent-employment person deduplication, active/leave composition, terminated exclusion, future-effective and late-recorded exclusion, FTE and unassigned-person reporting, deterministic canonical evidence, historical recorded-time reconstruction, duplicate-version rejection, overlapping-exclusive-employment rejection, position-seat over-allocation rejection, assignment-person integrity, per-employment allocation-integrity reuse, and timezone-aware knowledge cutoffs. `.github/workflows/foundation-ci.yml` checks out the exact candidate SHA and runs the complete HRIS kernel with the package's 100% statement and branch coverage threshold.

## References

The APA 7 reference and exact public ISO metadata used by this ADR are recorded in `docs/doctoring/workforce-composition-references.md`.
