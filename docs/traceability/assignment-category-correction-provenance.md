# Assignment category correction provenance traceability

Status: `implemented_on_active_pr` on Orgmetra PR #165. This document does not describe protected `develop` as shipped correction support.

## Decision boundary

Orgmetra owns Assignment category correction because Assignment, Employment, Person, Position, allocation, effective time, and system-recorded time are HRIS truth in the People/Organization–Job–Position–Assignment boundary. A correction is not an in-place category update. It closes one recorded-open explicit Assignment fact, creates a replacement with a new Assignment identity, and records a normalized predecessor→replacement provenance edge at the same system-recorded timestamp.

The replacement must preserve tenant, Employment, Person, Position, allocation, and effective interval. Only `assignment_category_code` changes between the two explicit values `primary` and `concurrent_secondary`. Historical `legacy_unspecified` rows remain outside this correction contract; classifying them requires a separately governed workflow rather than inference from allocation, ordering, or topology.

## Executable evidence

| Concern | Active-PR evidence | Required behavior |
|---|---|---|
| Domain replacement semantics | `packages/hris-kernel/src/orgmetra_hris_kernel/assignment_correction.py`; `packages/hris-kernel/tests/test_assignment_category_correction.py` | Close predecessor recorded time, create a new identity, preserve other Assignment truth, and link the two facts. |
| Runtime identity integrity | same kernel module/tests; `database/migrations/0002_sealed_evidence_digest.sql` | Correction-owned UUIDs are exact built-in UUID values and reject RFC 9562 Nil/Max sentinels before equality or provenance construction. |
| Runtime recorded-time integrity | same kernel module/tests | Correction provenance accepts only an exact built-in, offset-aware `datetime`; executable datetime subtypes and offsetless values fail closed. |
| Normalized persistence | `database/migrations/0018_assignment_category_supersession.sql` | One tenant-scoped append-only edge links exactly one predecessor and one replacement; forks and replacement reuse are rejected while later correction chains remain possible. |
| Database linkage integrity | `tests/test_assignment_category_correction_postgres.sh` | Predecessor close time equals edge time, replacement start equals edge time, replacement is recorded-open, business truth is unchanged, and explicit category truth changes. |
| Tenant/privacy boundary | migration 0018 RLS policy and composite tenant FKs | Cross-tenant provenance cannot be linked or read through the canonical tenant policy. |
| Hosted exact-head proof | `.github/workflows/assignment-correction-quality.yml` | Exact checkout runs the focused HRIS-kernel and PostgreSQL contracts on the current candidate head. Absence, queueing, or predecessor results are not GREEN evidence. |

## DDD mapping

- Bounded context: People / Organization–Job–Position–Assignment.
- Aggregate/entity: immutable `assignment_record` fact identified by `assignment_record_id`.
- Value object: explicit `assignment_category_code`.
- Domain service: `correct_assignment_category` produces the closed predecessor, replacement, and supersession fact; portfolio/capacity invariants remain authoritative validation prerequisites before persistence.
- Repository/persistence boundary: `assignment_supersession_record` is Orgmetra-owned normalized provenance and never a copied external contract.
- Invariants: tenant consistency, operational identities, strict system-time succession, preserved non-category business truth, explicit category change, one-to-one predecessor/replacement edge, append-only provenance, and tenant RLS.

No shared kernel or cross-service SQL is introduced. Keyverse remains the identity/authorization peer; it does not author Assignment truth.

## Remaining active-PR gap

PR #165 is not feature-complete or merge-ready merely because the domain and normalized persistence slices exist. The People correction command still must bind exact authorization, actor, purpose, human confirmation, evidence version, idempotency, audit/outbox, authoritative predecessor/Employment/Position locks, portfolio and seat-capacity revalidation, transactional rollback, concurrent-correction behavior, OpenAPI/API contract, and recovery evidence. Parent PR #163 must integrate first; the child must then be non-force restacked/retargeted and reacquire exact-head workflows and independent review.

The general recorded-interval and correction-helper trust boundaries remain owned by their canonical repair lanes rather than being copied into this feature branch.

## References

Allen, J. F. (1983). Maintaining knowledge about temporal intervals. *Communications of the ACM, 26*(11), 832–843. https://doi.org/10.1145/182.358434

Internet Engineering Task Force. (2024). *Universally unique IDentifiers (UUIDs)* (RFC 9562). https://doi.org/10.17487/RFC9562

Jensen, C. S., & Snodgrass, R. T. (1999). Temporal data management. *IEEE Transactions on Knowledge and Data Engineering, 11*(1), 36–44. https://doi.org/10.1109/69.755613
