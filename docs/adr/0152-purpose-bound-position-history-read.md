# ADR 0152: Purpose-bound bitemporal Position history read

- **Status:** Proposed
- **Date:** 2026-08-30
- **Owners:** Orgmetra People domain

## Context

Protected `develop` already models `position_record` separately from `job_profile`, `assignment_record`, and their time-varying facts. It also stores Position versions with business-effective (`effective_from`, `effective_to`) and system-recorded (`recorded_from`, `recorded_to`) intervals. A commercial HRIS still needs a buyer-visible way to inspect how one Position was understood over time without widening the read to Person, Assignment, compensation, candidate, or employment-decision data.

A Position-history read is a high-value governance boundary because historical workforce interpretation is frequently used in reorganizations, audit, workforce planning, and downstream validity analysis. Returning persistence rows directly would make authorization order, tenant scope, bitemporal interpretation, and field minimization depend on adapter behavior instead of the domain contract.

## Decision

Orgmetra adds a read-only `position_history` application boundary in the People service.

1. The caller supplies an exact operational tenant UUID, an exact operational Position UUID, an exact built-in UTC knowledge instant, a declared purpose, and an explicit requested-field set.
2. Trust-bearing request UUIDs are immediately reduced to exact built-in integer scalar authority. Fresh UUID views are reconstructed only when an existing authorization or persistence contract requires UUID values, so retained caller aliases cannot change the authorized tenant or Position after validation.
3. The concrete persistence capability is captured inertly from the repository type before authorization and the same exact function is invoked afterward. A post-decision instance lookup cannot substitute a different executable repository capability.
4. Purpose-bound authorization is evaluated **before** the injected read port may retrieve protected Position history. The authorized field schema is also validated before protected retrieval, including empty-result cases.
5. The persistence adapter returns immutable `PositionHistoryRecord` values. Trust-bearing UUID identities inside a row are stored as built-in integer scalars rather than retained UUID objects. Application code treats every row as untrusted evidence, revalidates raw scalar-backed state, reconstructs a detached trusted row, and then checks tenant and Position identity, system-time visibility, version uniqueness, and business-effective non-overlap.
6. System-recorded intervals are interpreted as half-open intervals: `recorded_from <= known_at < recorded_to`, with an absent `recorded_to` meaning open-ended visibility.
7. Business-effective intervals are also half-open. Two versions visible at the same knowledge instant may not claim overlapping business truth for the same Position. An absent business end is represented as **unbounded**, not by substituting a finite date sentinel such as `date.max`; this preserves overlap semantics even when a valid interval begins on Python's maximum representable date.
8. The response is deterministic and contains only fields explicitly authorized by the purpose-bound policy. Unknown fields and `str` subclasses fail closed rather than reaching reflection-based serialization.
9. `position_record_version_id`, organization lineage, Job lineage, status, business-effective dates, and system-recorded timestamps remain distinct concepts. The read does not collapse Job, Position, or Assignment.
10. The application boundary depends on an injected port. It does not query another service's application tables and does not introduce cross-service SQL.

## Trust and time semantics

The service accepts exact built-in UUID/date/datetime/timezone primitives at the trust boundary. Caller-controlled subclasses and timezone implementations are rejected. Exact outer type is not sufficient authority for UUIDs because a retained UUID object can be mutated through low-level object mechanisms after validation. The application therefore snapshots UUID identity to built-in integer scalars before authorization or protected retrieval and stores the same scalar authority inside Position-history records.

The persistence port is an executable trust boundary. Validation of one method lookup followed by a second dynamic lookup after authorization would create a checked-versus-used gap. The application captures the concrete class function before authorization, rejects missing/non-function/Protocol-placeholder implementations, and invokes that captured function directly after the access decision.

`known_at` is system-recorded time, not business-effective time. A version may be visible at `known_at` while describing a past or future business-effective period. These dimensions must never be substituted for one another.

Open-ended business time is a semantic infinity, not the largest finite date representable by one runtime. Overlap therefore uses direct endpoint-presence logic: a left interval is before a right end when the right end is absent or the left start is strictly earlier, and conversely for the right interval. This keeps half-open interval algebra correct at representational extremes and avoids treating `[date.max, ∞)` as empty.

## Data-model boundary

This ADR does not change protected-main storage. The existing schema remains authoritative:

- `job_profile` describes the reusable Job/work content.
- `position_record` is the tenant-owned Position anchor in an organization and references the Job profile.
- `position_record_version` carries Position status and business-effective/system-recorded version evidence.
- `assignment_record` links a worker/employment relationship to a Position and remains a separate lifecycle fact.

An adapter that materializes Position history must preserve those meanings and may not use the new view to imply that Assignment or Person history is part of a Position version.

## Consequences

### Positive

- HR operators can inspect Position history without broad Person/Assignment disclosure.
- Authorization-before-retrieval is executable and testable.
- Retained request/record UUID aliases and post-authorization repository substitution cannot silently change the protected target.
- Unsupported disclosure schema fails before persistence even when the result would be empty.
- Bitemporal contradictions fail closed at the service boundary, including valid extreme-date intervals whose end is genuinely unbounded.
- The module is standalone and can be extracted behind a service/API boundary later without rewriting its authorization and evidence semantics.
- Exact owned statement/branch coverage can be enforced independently of a future database adapter.

### Trade-offs

- The read port must deliberately materialize data that the application can validate; adapters cannot return arbitrary ORM entities.
- A database adapter must provide a transactionally coherent snapshot. The application checks cannot replace MVCC/snapshot isolation where concurrent database writes are possible.
- Static capability capture intentionally rejects unusual dynamic repository dispatch at this high-trust boundary.
- This slice exposes no HTTP route or write mutation. Those are separate bounded decisions and must not be inferred from this ADR.

## Verification

PR #152 records a hosted test-first sequence. A test-only head failed because the production Position-history module did not exist. The smallest application implementation then satisfied the behavioral contract, after which a remaining 100%-coverage branch for malformed low-level row reconstruction was covered with an explicit fail-closed regression rather than by excluding code or weakening the gate.

A later source sweep found that open-ended business intervals were approximated with `date.max` during overlap checks. Test-only head `af8d0b9b88c50f17c87eb8ecf1eea29918835dce` produced genuine hosted RED in People API Quality run `33267978859`, job `99141335635`: 157 existing tests passed, exact owned coverage remained 100%, but the new extreme-date regression failed because `[date.max, ∞)` was incorrectly treated as non-overlapping with an earlier open interval. Root repair `955956f838c467c06c25b63127b7c6e976dea812` removes the finite-infinity sentinel and compares optional interval ends directly.

After repository workflow consolidation reached protected `develop`, PR #152 adopted that protected truth by ordinary two-parent merge rather than retaining its stale pre-consolidation base. A new test-only head then fixed four additional trust contracts in source: constructor UUID aliases must not retain authority, request Position identity must survive post-authorization mutation attempts, unsupported authorized fields must fail before an empty persistence read, and repository execution must use the capability captured before authorization. Production repair snapshots request and record identity to built-in integer scalars, validates disclosure schema before retrieval, and statically binds the repository function.

This ADR remains **Proposed** until the exact current implementation is integrated into protected `develop`. Predecessor evidence is non-transferable; every material head must reacquire applicable hosted checks and qualifying independent review.
