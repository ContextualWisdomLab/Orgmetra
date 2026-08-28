# Position lifecycle application traceability

## Truth state

- **Protected-main truth:** `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` has stable Position anchors, bitemporal PositionVersion facts, Assignment occupancy, tenant RLS, and immutable audit/outbox foundations, but no authoritative existing-Position lifecycle mutation.
- **Dependency-active truth:** PR #111 adds only reviewed lifecycle evidence and remains a separate review boundary.
- **Active PR truth:** this stacked branch applies an approved v1 review to locked current Position/Assignment truth, requires the exact reviewed snapshot digests to match freshly recomputed authoritative truth, and records the resulting bitemporal PositionVersion plus immutable application/audit/outbox correlation.
- **Planned after parent integration:** retarget to fresh `develop`, reconcile migration/repository inventories, and rerun all applicable Foundation, Security, SAST, Recovery, People and lifecycle-application gates on one exact head.
- **Out of scope:** Person/candidate data, compensation, assessment/rating data, reporting-line changes, autonomous employment decisions, foreign repository writes, and direct foreign application-table SQL.

## Requirement mapping

| Requirement | Evidence |
|---|---|
| Stable Position identity with versioned lifecycle state | existing `position_record`; `position_record_version`; ADR 0112 |
| Separate business and system time | reviewed `effective_on`; predecessor split; PostgreSQL `transaction_timestamp()` for new system-time truth |
| Stale-review defense | locked current Position and exact predecessor/status comparison before application |
| Fresh Position snapshot binding | `position_lifecycle_position_snapshot_digest(...)` hashes the current anchor + system-visible PositionVersion at the reviewed business date; reviewed digest must match exactly |
| Fresh Assignment snapshot binding | `position_lifecycle_assignment_snapshot_digest(...)` deterministically hashes value-minimized current occupancy at the reviewed business date; reviewed digest must match exactly |
| Canonical review bytes | `position_lifecycle_review_canonical_json(...)` produces compact key-sorted object bytes; the validator rejects semantically equivalent noncanonical encodings even with a recomputed SHA-256 |
| Staffing safety | current Assignment overlap check blocks `closed`/`abolished` transitions |
| Human review remains non-authorizing | exact v1 review state must be `approved_for_authoritative_resolution` while application independently re-resolves live truth |
| Actor separation | requester/reviewer from review plus distinct application actor |
| Immutable review correlation | exact canonical review bytes + SHA-256 + review UUIDv4 stored in `position_lifecycle_application_record` |
| Immutable audit/outbox | same-transaction `record_audit_outbox_event`; application trigger binds event subject/actor/purpose/reason/evidence/result/confirmation and outbox identity |
| Correction, not rewrite | PositionVersion history trigger permits only closing an open recorded interval at transaction time; application evidence is append-only |
| Tenant isolation | tenant-qualified FKs and forced-RLS application relation; existing PositionVersion forced-RLS remains intact |
| Explicit mutation privilege | migration 0025 revokes PostgreSQL default `PUBLIC EXECUTE` from `apply_position_lifecycle_change(...)`; intended application-role execution must be granted deliberately |
| Value minimization | no Person/candidate identity, pay, rating, assessment, prompt/model output, or free-form HR text in application evidence; Assignment snapshot evidence is stored only as SHA-256 |
| Exact-head quality | dedicated PostgreSQL regression applies migration 0025, proves positive fresh-snapshot application, rejects forged/noncanonical review evidence, checks default PUBLIC execution is absent, and runs under a pinned exact-checkout workflow |

## Buyer behavior

An HR operator can review a Position freeze, closure, abolition, or reactivation in #111. This branch does not trust that review as current truth: at application time it reopens the exact tenant/Position state, confirms the reviewed predecessor still covers the business date, recomputes the reviewed Position and Assignment snapshot digests, prevents closure/abolition across live staffing, then writes correction-preserving PositionVersion truth with immutable audit/outbox. If any scope, status, canonical evidence, reviewed snapshot, chronology, actor-separation, or staffing condition changed, the application fails closed and the buyer must review the fresh state rather than silently applying stale intent.
