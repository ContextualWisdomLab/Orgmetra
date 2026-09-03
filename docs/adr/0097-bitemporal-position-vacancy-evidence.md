# ADR 0097: Position vacancy is bitemporal aggregate evidence

## Status

Proposed on PR #97 only. This is not protected-`develop` product truth until the exact owning head integrates.

## Context

Orgmetra already models Position as a durable seat and Assignment as a bitemporal allocation to that seat. Buyers still need a defensible answer to a common workforce-operations question: at a stated business date and knowledge cutoff, how many staffable Positions were vacant, partially staffed, or fully staffed? Deriving that result from current rows or worker exports would erase historical knowledge-time semantics or create unnecessary row-level PII exposure.

ISO 30414:2025 is the current second edition of the international human-capital reporting/disclosure standard and includes workforce composition among its core reporting areas. Orgmetra uses the public ISO metadata as design traceability only; this ADR does not reproduce licensed metric definitions and does not claim ISO conformity or certification.

## Decision

Orgmetra exposes `PositionVacancySnapshot` and `build_position_vacancy_snapshot(...)` as a descriptive HRIS-kernel boundary.

- The query coordinate is `(tenant_record_id, effective_on, known_at)`.
- Exactly one visible Position version may define one Position identity at that coordinate.
- `active` and `open` Position versions are staffable; `closed`, `frozen`, and `abolished` are non-staffable.
- Unknown visible Position statuses fail closed instead of disappearing from the denominator.
- Every visible Assignment must pass the existing Position coverage and seat-capacity rules.
- One Assignment identity may resolve to at most one visible Assignment fact; duplicate visible identity fails closed before allocation is counted.
- Allocation `0` is vacant, `(0, 1)` is partially staffed, and exactly `1.0000` is fully staffed. Existing seat-capacity integrity rejects totals above `1.0000`.
- Canonical evidence contains only tenant, effective/system coordinates, aggregate Position counts, aggregate staffed FTE, and schema version. It excludes Person, Employment and Assignment identifiers and all human-readable PII.
- SHA-256 addresses the exact canonical UTF-8 representation for audit correlation.
- The result is descriptive evidence only and cannot authorize recruiting, hiring, transfer, termination, compensation, scheduling, or another high-impact employment action.

## Consequences

The slice gives buyers historically reconstructable vacancy/fill evidence without a shadow worker database. Contradictory Position truth, duplicate visible Assignment identity, stale Assignment coverage, unknown Position status and seat overfill remain data-integrity errors rather than being normalized into plausible metrics.

This slice does not implement requisition creation, headcount budget approval, workforce forecasting, low-cell suppression, dashboard UI or an employment decision policy. Those remain separate governed boundaries.

## Verification

`packages/hris-kernel/tests/test_position_vacancy.py` covers tenant isolation, vacant/partial/full classification, fractional multiple membership, bitemporal visibility, unknown status, stale non-staffable Assignment, overfilled Position, duplicate visible Assignment identity, direct snapshot invariants, unrepresentable UTC cutoffs, PII-minimized canonical evidence and deterministic digest. Existing Workforce Intelligence/Foundation/SAST/Security/Recovery gates must pass on one unchanged exact head.

## Reference

See `docs/doctoring/position-vacancy-references.md`.
