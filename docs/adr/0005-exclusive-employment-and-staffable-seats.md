# ADR 0005: Exclusive employment and staffable seats

## Status

Status: Accepted

## Context

ADR 0004 bound assignments to a named employment and split employment/position identity from versioned status. Buyers still could not:

- record employment, position, or assignment through the published API;
- prevent one person from holding two unmarked exclusive jobs on the same days;
- prevent two people from consuming more than 1.0000 of one seat;
- stop an assignment after a seat was closed, frozen, or abolished.

A later implementation also exposed an authority/concurrency ambiguity: `candidate_worker_conversion_record` is recruiting-origin provenance bound to a particular hire decision, Person, and resulting Employment. Treating a current conversion row as the generic prerequisite or serialization root for later Employment/Assignment writes makes historical recruiting provenance an accidental authorization mechanism and fails for legitimate People-admin Employments that did not originate from that recruiting conversion.

Allen (1983) treats interval overlap as a first-class relation. Diez-Roux (1998) and Robinson (1950) warn that treating nested assignments as independent atoms hides unit-level over-allocation. ISO 30414:2025 requires reconstructable workforce counts. Jensen and Snodgrass (1999) require a knowledge cutoff so a later freeze cannot rewrite what was known earlier.

## Decision

- `employment_record_version.employment_concurrency_code` is `exclusive` or `concurrent`. Exclusive periods for one person cannot overlap.
- Generic Employment creation serializes on the tenant-qualified current `person_record`, then re-reads that Person's Employment portfolio in a fresh READ COMMITTED statement before applying exclusivity checks.
- Generic Assignment creation serializes first on the named tenant-qualified `employment_record`, then on the named `position_record`, and evaluates Employment eligibility plus Employment/Position allocation from snapshots taken after the relevant conflict locks. Employment separation uses the same Employment aggregate conflict root.
- `candidate_worker_conversion_record` remains governed recruiting/hire provenance and analytic lineage. It is not generic Employment or Assignment mutation authority and is not the concurrency root for staffing an already authoritative Employment.
- `orgmetra_hris_kernel` 0.4.0 rejects assignments that are not covered by an `active` or `open` position version.
- Visible allocations for one `position_record_id` cannot exceed 1.0000 on a reconstructed day.
- `POST /v1/employment-records`, `POST /v1/position-records`, and `POST /v1/assignment-records` reuse the same Keyverse mutation context, human confirmation, and versioned evidence composition as other high-impact commands.

## Consequences

- HR can create an Employment through an authorized People-admin path and later staff it without fabricating or reusing recruiting conversion evidence.
- Recruiting-origin conversion continues to prove the hire lineage for recruiting, validity-study, and related evidence flows without becoming a generic People write gate.
- Different idempotency keys cannot validate the same stale Employment allocation/eligibility portfolio merely because they do not share a recruiting conversion key; the Employment root is the stable conflict boundary.
- Assignment/separation races are coordinated on the same Employment aggregate, while seat-capacity races remain coordinated on Position.
- A second job must be marked concurrent, or the prior exclusive period must end, before save.
- Closing or freezing a seat fails later assignment days even when employment coverage remains valid.
- Persistence still applies these kernel checks before insert; this ADR does not make recruiting evidence optional where a recruiting-specific contract explicitly requires it.

## References

See `docs/doctoring/REFERENCES.md` for the APA 7th records cited above, including Allen (1983), Diez-Roux (1998), Robinson (1950), ISO 30414:2025, and Jensen and Snodgrass (1999).
