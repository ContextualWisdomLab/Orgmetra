# ADR 0131: Persist reviewed Employment work-capacity truth as effective points

- **Status:** Proposed — active only on PR #128 until parent #103 integrates and this child is revalidated on fresh `develop`.
- **Decision owner:** Orgmetra HRIS core.
- **Parent contract:** PR #103 `EmploymentWorkCapacityReviewPacket`.

## Context

Orgmetra already distinguishes Person, Employment, Job, Position and Assignment. PR #103 adds a non-authorizing human-review packet for one proposed Employment work-capacity change, but a review packet is not authoritative HRIS truth. Buyers need a durable answer to “what contracted work capacity did this Employment have on business date X, as known by the system at time Y?” without deriving that fact from Assignment allocation, payroll, leave, disability/medical data, or another service's application tables.

## Decision

Add two 3NF relations owned by the HRIS core:

1. `employment_work_capacity_record` — one stable tenant-qualified capacity identity per Employment.
2. `employment_work_capacity_version` — one human-reviewed capacity **effective point** plus system-recorded interval and immutable evidence correlations.

A capacity point means “from `effective_on`, use this capacity ratio until a later effective point supersedes it for business-time resolution.” `resolve_employment_work_capacity(tenant, employment, effective_on, known_at)` selects the latest effective point not after the requested business date among versions visible at the requested system-knowledge time. This avoids rewriting the previous business row every time a future capacity change is approved while preserving both business-effective and system-recorded history.

The first persisted capacity point is a bounded bootstrap. It may rely only on the exact reviewed employment-terms/capacity-policy evidence bound by parent #103 and becomes authoritative **from its own `effective_on` forward**; it does not invent pre-bootstrap capacity history. Every later normal change must match the already-authoritative capacity resolved at its proposed effective date before a new point can be appended.

Normal application is also **forward-only**. Once a later effective point is authoritative, a newly recorded earlier/same effective point could invalidate the reviewed `current_capacity_ratio` premise of that later point. Migration 0032 therefore rejects normal inserts whose `effective_on` is not after the latest currently system-visible point. Retroactive correction is not silently forbidden as a business need; it requires a separate correction/replay boundary that closes affected system-time versions, revalidates every downstream effective point in order, and emits new immutable evidence. That broader replay operation is outside this bounded slice.

## Authority and evidence boundary

`apply_employment_work_capacity_change(...)` is a distinct application boundary. It:

- requires the session tenant to equal the requested tenant;
- binds exact parent review JSON bytes to their SHA-256 and revalidates the parent review key set, tenant/Employment scope, fixed non-authorizing governance state, human-review requirement, reason code, actor separation, evidence version, capacity scale and review chronology;
- requires the review JSON bytes themselves to equal the parent's deterministic compact, C-key-sorted representation; semantically equivalent reordered or whitespace-altered JSON is rejected even if a caller recomputes SHA-256;
- requires a third actor to apply the reviewed change, distinct from requester and reviewer;
- requires opaque review-audit, application-audit and application-outbox correlations and SHA-256 envelope evidence without querying another service's application tables;
- serializes one tenant-qualified Employment's capacity mutations with a transaction-scoped advisory lock;
- requires an `active` or `leave` Employment version at `effective_on` as visible at the database transaction time;
- derives normalized persistence fields from the reviewed JSON rather than trusting duplicate caller-supplied values; and
- revokes `PUBLIC` execution. Production deployment must grant the function only to the purpose-authorized Orgmetra host role after that host resolves reviewer/applier authority and immutable audit/outbox contracts.

The canonical-byte rule is an evidence-identity boundary, not cosmetic JSON formatting. Parent #103 signs one deterministic UTF-8 representation using sorted keys and compact separators. Allowing alternate whitespace/key order plus a caller-recomputed digest would create multiple durable byte identities for one reviewed fact and break exact audit correlation. Migration 0033 therefore rejects any alternate representation before durable work-capacity truth is accepted.

The persisted relation does **not** store medical/disability detail, legal leave reasons, payroll values, compensation amounts, ratings, candidate data, free-form personal notes, prompts, or model output. A capacity ratio is necessary authorized Employment-terms data; it is not an employment suitability decision and does not authorize compensation, scheduling, leave, payroll or Assignment mutation.

## Temporal and integrity semantics

PostgreSQL `transaction_timestamp()` supplies one stable system-recorded time for each application transaction. A GiST exclusion constraint prevents two system-visible claims for the same capacity identity and the same `effective_on`. Historical rows are immutable except for closing an open system-recorded interval at the current transaction timestamp; corrections are correction-not-rewrite and must emit replacement evidence through an explicit correction/replay contract rather than editing prior truth.

The first capacity point carries `bootstrap_from_reviewed_terms`; subsequent forward points carry `matched_authoritative_capacity`. Tenant RLS is enabled and forced on both relations, while a tenant-scoped read role must be `NOSUPERUSER NOBYPASSRLS` in production verification.

## Concurrency

The application boundary takes `pg_advisory_xact_lock` over the tenant-qualified Employment before anchor creation/current-capacity comparison. Migration 0032's forward-chain trigger takes the same transaction-scoped lock before checking the latest effective point. PostgreSQL transaction-level advisory locks are held until transaction end; hash collisions may over-serialize but cannot weaken the invariant. This prevents two concurrent reviewed changes from both validating against the same stale current-capacity truth and then independently appending contradictory next states.

## Consequences

- Capacity becomes an authoritative Employment fact instead of an inference from Assignment allocation.
- Business-effective and system-recorded history remain distinct.
- Parent review evidence remains non-authorizing; application is a separate controlled act.
- One reviewed packet has one durable canonical byte identity; alternate JSON formatting cannot be re-hashed into a second accepted evidence representation.
- Audit/outbox stay contract correlations rather than direct cross-service SQL.
- The initial bootstrap explicitly limits truth to its own effective date forward.
- Normal changes cannot be inserted retroactively underneath already-authoritative downstream points; replay is a separate governed operation.
- This PR remains dependency-first under #103. Parent checks/reviews never transfer; after parent integration this branch must retarget to fresh `develop` and rerun every applicable local and central gate.

## References

See `docs/doctoring/employment-work-capacity-persistence-references.md` for the primary PostgreSQL documentation used for transaction time, exclusion constraints, advisory locking and row-level security.
