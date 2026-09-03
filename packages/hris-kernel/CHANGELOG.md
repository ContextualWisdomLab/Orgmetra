# Changelog

## Unreleased

- Add `WorkforceCompositionChangeSnapshot` for deterministic same-tenant comparison of two effective-date workforce-composition states at one exact recorded-time cutoff.
- Report aggregate net changes for distinct-person headcount, reportable employments, staffed assignments, staffed Decimal FTE, unassigned people, and status counts without serializing row-level HR identities.
- Fail closed on cross-tenant endpoints, non-forward effective dates, and different knowledge cutoffs so recorded corrections cannot masquerade as business-time workforce movement.
- Freeze timezone-aware knowledge cutoffs to detached UTC datetimes and copy status-count containers before canonical serialization, preventing mutable caller objects or timezone providers from changing snapshot evidence after construction.
- Canonicalize every mathematical staffed-FTE zero to exact `0.0000`, reject oversized nonzero evidence against staffed-assignment capacity before any representation expansion, normalize accepted direct FTE to four fractional places, and recheck that representation during export.
- Canonicalize employment-status evidence by requiring exact two-value `(str, int)` rows, rejecting malformed/boolean/negative counts with governed domain errors, and omitting semantic zero-count rows so equivalent aggregates have one JSON/hash representation.
- Revalidate every workforce aggregate and temporal invariant immediately before canonical JSON or digest export, so low-level post-construction mutation cannot become new audit evidence.
- Revalidate comparison endpoint runtime types, tenant identity, forward effective-date order, and one exact knowledge cutoff immediately before change-evidence export, preventing low-level endpoint mutation from bypassing the constructor contract.
- Require every allocation ratio reaching employment-portfolio or Position-seat aggregation to be an exact finite `Decimal` in `(0, 1.0000]` with at most four fractional places, preventing extreme-scale values from reaching exact coefficient arithmetic.
- Keep the contract descriptive: endpoint deltas are not labeled as hires, separations, transfers, turnover, causes, forecasts, protected-attribute effects, or employment recommendations.
