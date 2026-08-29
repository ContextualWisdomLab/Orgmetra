# ADR 0005: Exclusive employment and staffable seats

## Status

Status: Accepted

## Context

ADR 0004 bound assignments to a named employment and split employment/position identity from versioned status. Buyers still could not:

- record employment, position, or assignment through the published API;
- prevent one person from holding two unmarked exclusive jobs on the same days;
- prevent two people from consuming more than 1.0000 of one seat;
- stop an assignment after a seat was closed, frozen, or abolished.

Allen (1983) treats interval overlap as a first-class relation. Diez-Roux (1998) and Robinson (1950) warn that treating nested assignments as independent atoms hides unit-level over-allocation. ISO 30414:2025 requires reconstructable workforce counts. Jensen and Snodgrass (1999) require a knowledge cutoff so a later freeze cannot rewrite what was known earlier.

## Decision

- `employment_record_version.employment_concurrency_code` is `exclusive` or `concurrent`. Exclusive periods for one person cannot overlap.
- `orgmetra_hris_kernel` 0.4.0 rejects assignments that are not covered by an `active` or `open` position version. At one recorded knowledge cutoff, overlapping effective position versions fail closed only when their statuses differ; repeated evidence for one unchanged status is not treated as contradictory.
- Visible allocations for one `position_record_id` cannot exceed 1.0000 on a reconstructed day.
- `POST /v1/employment-records`, `POST /v1/position-records`, and `POST /v1/assignment-records` reuse the same Keyverse mutation context, human confirmation, and versioned evidence composition as other high-impact commands.

## Consequences

- HR can hire, open a seat, and assign a worker through the contract instead of only through kernel fixtures.
- A second job must be marked concurrent, or the prior exclusive period must end, before save.
- Closing or freezing a seat fails later assignment days even when employment coverage remains valid.
- Persistence still applies these kernel checks before insert; this ADR does not add HTTP handlers.

## References

See `docs/doctoring/REFERENCES.md` for the APA 7th records cited above, including Allen (1983), Diez-Roux (1998), Robinson (1950), ISO 30414:2025, and Jensen and Snodgrass (1999).
