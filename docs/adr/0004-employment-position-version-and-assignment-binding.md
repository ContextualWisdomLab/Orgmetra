# ADR 0004: Employment and position versions bind assignments

## Status

Status: Accepted

## Context

Organization and job already separate durable anchors from bitemporal versions. Employment and position still stored status and effective time on the identity row, so a correction minted a new identity and orphaned transitions or assignments. Assignments named only a person and a position, so a worker could be assigned without an employment or onto another worker's employment.

Jensen and Snodgrass (1999) require an explicit knowledge cutoff for temporal reconstruction. Snodgrass (1999) separates valid time from transaction time. Robinson (1950) and Diez-Roux (1998) warn that individual assignments nested in units and float pools cannot be treated as independent atoms.

## Decision

- `employment_record` and `position_record` are durable anchors.
- Mutable status and effective/recorded intervals live in `employment_record_version` and `position_record_version`.
- Single-valued version families use gist exclusions on tenant, identity, effective range, and recorded range.
- `assignment_record` references `(tenant_record_id, employment_record_id, person_record_id)` so the assigned worker is the worker on that employment.
- Allocation totals are a multiple-membership rule enforced by `orgmetra_hris_kernel`, not a single-valued exclusion.

## Consequences

- Retroactive employment or position corrections keep the same identity.
- Historical queries can reconstruct what was true and what was known.
- Assignments cannot detach from employment coverage.
- Multiple concurrent assignments remain legal when their allocations stay at or below 1.0000 for one employment.
