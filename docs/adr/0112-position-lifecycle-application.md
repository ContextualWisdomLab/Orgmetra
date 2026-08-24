# ADR 0112: Apply reviewed Position lifecycle changes as bitemporal truth

Status: Proposed

## Context

PR #111 adds a human-reviewed, deliberately non-authorizing `PositionLifecycleChangeReviewPacket`. Protected `develop` already separates stable `position_record` identity from bitemporal `position_record_version`, and Assignment truth separately represents worker occupancy. A commercial HRIS still needs an authoritative boundary that can turn an approved lifecycle proposal into Position truth without treating stale UI state or the review artifact itself as authority.

Closing or abolishing an occupied Position is high-impact because it can make staffing truth internally inconsistent. Rewriting a PositionVersion in place would also destroy what the system previously knew.

## Decision

Add an Orgmetra-owned Position lifecycle application boundary. It consumes exact v1 canonical review evidence, revalidates its SHA-256 and governed shape, locks the tenant-qualified Position, resolves the exact PositionVersion covering the requested business-effective date at current system time, rejects stale reviewed status, and checks current Assignment occupancy before `closed` or `abolished` transitions.

Application closes only the predecessor system-recorded interval at PostgreSQL transaction time. When the reviewed effective date splits an existing business-effective interval, it inserts a preserved predecessor segment plus the reviewed successor segment at the new system-recorded time. The stable Position identity is unchanged.

One immutable `position_lifecycle_application_record` binds predecessor/successor identities, exact review bytes/digest, requester/reviewer/applier separation, lifecycle reason, human-review chronology, and the audit/outbox identities. The audit/outbox event is created in the same transaction and must match Position subject, purpose, reason, review digest, applier, high-impact result, and human-confirmation reference. Application evidence and PositionVersion history reject UPDATE/DELETE rewrite; tenant-scoped application evidence uses forced row-level security.

## Consequences

- Business-effective time and system-recorded time remain independent and reconstructable.
- A review packet never authorizes mutation by itself; current Position and Assignment truth is re-resolved at application time.
- `closed` and `abolished` fail closed while any current Assignment overlaps the requested effective date or later.
- Existing Assignment, reporting-line, compensation, assessment, and Person facts remain separate; no cross-service table SQL is introduced.
- The branch is a dependency-first descendant of #111 and remains Draft until the parent integrates and fresh post-restack gates pass.
- Direct production database privileges remain a deployment concern; this slice does not claim that PostgreSQL row-level security replaces application authorization.

## Alternatives rejected

1. **Overwrite `position_record_version.position_status_code`.** Rejected because it destroys system-time history.
2. **Create a new Position identity for each lifecycle change.** Rejected because Job/Position/Assignment semantics require a stable Position anchor with versioned state.
3. **Apply the review without refreshing Assignment truth.** Rejected because a reviewed closure can become stale before application and strand active staffing evidence.
4. **Move lifecycle state into reporting or vacancy tables.** Rejected because those relations own different facts and would violate the Job/Position/Assignment model.