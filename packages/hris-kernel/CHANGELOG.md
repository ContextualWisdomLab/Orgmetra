# Changelog

## Unreleased

- Add `WorkforceCompositionChangeSnapshot` for deterministic same-tenant comparison of two effective-date workforce-composition states at one exact recorded-time cutoff.
- Report aggregate net changes for distinct-person headcount, reportable employments, staffed assignments, staffed Decimal FTE, unassigned people, and status counts without serializing row-level HR identities.
- Fail closed on cross-tenant endpoints, non-forward effective dates, and different knowledge cutoffs so recorded corrections cannot masquerade as business-time workforce movement.
- Freeze timezone-aware knowledge cutoffs to detached UTC datetimes and copy status-count containers before canonical serialization, preventing mutable caller objects or timezone providers from changing snapshot evidence after construction.
- Reject non-`Decimal` staffed FTE and boolean, negative, or non-integer per-status employment counts during direct workforce snapshot construction before arithmetic or canonical serialization.
- Keep the contract descriptive: endpoint deltas are not labeled as hires, separations, transfers, turnover, causes, forecasts, protected-attribute effects, or employment recommendations.
