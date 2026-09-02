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
| Purpose-bound correction command | `services/people-api/src/orgmetra_people_api/assignment_correction_mutations.py`; `services/people-api/tests/test_assignment_correction_mutations.py` | Authorize exactly the predecessor Assignment's category field for `correct_record`; require human confirmation/evidence version/idempotency; bind semantic replay to predecessor/category/evidence while excluding retry-generated record IDs. |
| Normalized persistence | `database/migrations/0018_assignment_category_supersession.sql` | One tenant-scoped append-only edge links exactly one predecessor and one replacement; forks and replacement reuse are rejected while later correction chains remain possible. |
| Database linkage and recovery | `tests/test_assignment_category_correction_postgres.sh` | Migration late-failure rollback is atomic; predecessor close time equals edge time; replacement start equals edge time; non-category business truth is unchanged; explicit category truth changes; append-only and one-to-one lineage fail closed. |
| Tenant/privacy boundary | migration 0018 RLS policy/composite tenant FKs plus the PostgreSQL regression | A NOBYPASSRLS reader sees no provenance without tenant context, sees its own tenant, and cannot see another tenant's provenance. |
| Hosted exact-head proof | `.github/workflows/assignment-correction-quality.yml` | Exact checkout runs the focused HRIS-kernel, People command, and PostgreSQL contracts on the current candidate head. Absence, queueing, or predecessor results are not GREEN evidence. |

## DDD mapping

- Bounded context: People / Organization–Job–Position–Assignment.
- Aggregate/entity: immutable `assignment_record` fact identified by `assignment_record_id`.
- Value object: explicit `assignment_category_code`.
- Domain service: `correct_assignment_category` produces the closed predecessor, replacement, and supersession fact; portfolio/capacity invariants remain authoritative validation prerequisites before persistence.
- Application service: `correct_assignment_record_category` owns the purpose-bound authorization boundary for the exact predecessor category field before the write port is called.
- Repository/persistence boundary: `assignment_supersession_record` is Orgmetra-owned normalized provenance and never a copied external contract.
- Invariants: tenant consistency, operational identities, strict system-time succession, preserved non-category business truth, explicit category change, one-to-one predecessor/replacement edge, append-only provenance, tenant RLS, and semantic replay consistency.

No shared kernel or cross-service SQL is introduced. Keyverse remains the identity/authorization peer; it evaluates the purpose-bound access request but does not author Assignment truth.

## Remaining active-PR gap

PR #165 is not feature-complete or merge-ready merely because the domain, command, and normalized persistence slices exist. The PostgreSQL People correction adapter still must bind the authorized command to one tenant-scoped transaction: acquire authoritative predecessor/Employment/Position locks, obtain the database-owned post-lock timestamp, re-run assignment portfolio and seat-capacity invariants, close the predecessor, insert the replacement and supersession edge, and persist idempotency plus audit/outbox evidence with rollback and concurrent-correction regressions. The command also still needs its HTTP/OpenAPI surface, top-level architecture/ERD/UML/security/operability/recovery alignment, canonical repository-inventory handoff, and exact-current-head hosted evidence. Parent PR #163 must integrate first; the child must then be non-force restacked/retargeted and reacquire exact-head workflows and independent review.

The general recorded-interval and correction-helper trust boundaries remain owned by their canonical repair lanes rather than being copied into this feature branch.

## References

Allen, J. F. (1983). Maintaining knowledge about temporal intervals. *Communications of the ACM, 26*(11), 832–843. https://doi.org/10.1145/182.358434

Internet Engineering Task Force. (2024). *Universally unique IDentifiers (UUIDs)* (RFC 9562). https://doi.org/10.17487/RFC9562

Jensen, C. S., & Snodgrass, R. T. (1999). Temporal data management. *IEEE Transactions on Knowledge and Data Engineering, 11*(1), 36–44. https://doi.org/10.1109/69.755613
