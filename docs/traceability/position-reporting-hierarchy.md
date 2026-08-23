# Position reporting hierarchy traceability

## Protected-main truth

At protected `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`, Orgmetra separates Job, Position and Assignment and stores organization-unit parentage, but it has no position-to-position reporting fact. A manager therefore cannot be reconstructed from protected-main authoritative HRIS facts without incorrectly inferring supervision from a worker assignment or an organization-unit parent.

## Active PR

PR #94 adds an in-memory HRIS-kernel contract for bitemporal solid-line Position reporting. `PositionReportingRelationship` binds one subordinate Position to one manager Position with tenant, effective/business-time, and system-recorded-time scope. `build_position_reporting_snapshot(...)` reconstructs one tenant's hierarchy at an explicit coordinate and returns deterministic subordinate-to-manager pairs.

The active contract fails closed when:

- one subordinate resolves to two visible solid-line managers;
- either endpoint does not resolve to exactly one same-tenant `active` or `open` Position version;
- a position reports to itself or the visible graph contains a cycle;
- caller-defined relationship/position/date/datetime runtime subclasses attempt to control trust-bearing comparisons;
- the system knowledge timestamp is naive, has no concrete UTC offset, or its timezone implementation raises during offset resolution.

Routine representations redact position-correlation UUIDs. The snapshot is descriptive organizational evidence, not a Person-manager link and not employment-decision authority.

## RED and repair evidence

- RED contract commit: `36f8f7d0605688c95ddebdc6d6f513eb81d4e144`.
- Foundation CI run `32616830004`, job `97138821309`, checked out that exact SHA and failed at `ModuleNotFoundError: No module named 'orgmetra_hris_kernel.position_reporting'` after the existing 171-test collection reached the missing owner boundary.
- Root implementation commit: `f75ef9a7d785229d2e8a11fe3a5257ce40a5e0c8`.
- The first implementation run then exposed an exact-coverage defect rather than a product-behavior failure: Workforce Intelligence run `32616862967`, job `97138902601`, passed all 181 tests but reported 95% coverage for the new module with missing trust-boundary branches.
- Follow-up adversarial regressions cover invalid UUID identity, unresolved/raising timezone offsets, and validation-bypassing PositionVersion runtime subtypes. The production timezone failure path is no longer excluded from coverage.

Only exact-current-head terminal workflow results may be treated as final GREEN evidence.

## Accepted architecture

Reporting authority belongs to Position, not Person. Assignment remains the independent, potentially multiple-membership fact that connects a person/employment to a seat. Organization-unit parentage remains a separate structural hierarchy and must not be repurposed as a manager relationship.

## Planned / not yet production-complete

PR #94 deliberately does **not** claim authoritative persistence or mutation. A later bounded owner slice must provide a normalized tenant-qualified persistence model, immutable audit/outbox evidence for reporting-line changes, bitemporal write/correction semantics, purpose-bound authorization, and database-level integrity without duplicating Person or Assignment data. UI organization-chart work is also separate and must receive Product Design/Figma/Storybook/accessibility evidence when it enters scope.

## Out of scope

No Keyverse, Naruon, contextual-orchestrator, Semantic Data Portal, or other dedicated-writer repository is modified. No cross-service application-table SQL is introduced.