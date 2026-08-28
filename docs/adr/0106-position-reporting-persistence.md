# ADR 0106 — Bitemporal Position reporting persistence

- Status: Proposed
- Active PR: #106; not protected-main truth
- **Decision date:** 2026-08-24
- **Parent contract:** PR #94, `feat/position-reporting-hierarchy@3f67182bb3065f2fc8fd974bfdd75a390d8a8fdc`

## Context

Protected `develop` separates Job, Position, Assignment, and organization-unit hierarchy but does not persist Position-to-Position supervisory relationships. PR #94 adds an in-memory bitemporal solid-line reporting snapshot and explicitly leaves persistence as later work. A commercial HRIS needs durable relationship truth without deriving a manager from the worker currently occupying a Position or from the organization-unit tree.

## Decision

Orgmetra persists a solid-line reporting relationship as a normalized anchor/version pair:

- `position_reporting_relationship_record` owns stable tenant, subordinate Position, and relationship type identity.
- `position_reporting_relationship_version` owns manager Position plus effective/business and recorded/system time for each reviewed application.
- one `(tenant, subordinate Position, relationship type)` anchor exists, so manager changes are versions rather than duplicate relationship identities;
- the version table carries only evidence needed to prove reviewed application: a SHA-256 review-evidence digest, the exact SHA-256 digest of the immutable application audit envelope, pseudonymous reviewer and applying actors, review time, audit correlation, and fixed application state;
- Person, Assignment, worker identity, compensation, performance rating, assessment output, and free-form HR text are not columns in this relation.

New recorded intervals use PostgreSQL `transaction_timestamp()` and begin open. History cannot be rewritten or deleted; the only row update is closing one open recorded interval at the transaction timestamp. `TRUNCATE` is rejected separately. Both relations use `ENABLE ROW LEVEL SECURITY` plus `FORCE ROW LEVEL SECURITY` and tenant policies based on `current_tenant_record_id()`.

A version insert fails closed unless it has an open same-tenant anchor, a different reviewer and applying actor, immutable same-tenant audit/outbox evidence for purpose `position_reporting_change_apply` with governed reason `approved_reporting_line_change`, no self-reporting edge, and no management cycle over an overlapping effective period. The application audit event must carry the exact reviewed-evidence digest in `orgmetraevidence`; the version's application-evidence digest must equal the persisted audit envelope digest. This prevents a syntactically valid reviewer/digest pair—or a semantically unrelated audit reason—from being recorded as evidence for the reporting-line application. Composite foreign keys bind both subordinate and manager Position IDs to the same tenant.

The database also enforces the staffable endpoint contract already defined by parent PR #94. At the proposed relationship version's system-recorded coordinate, both the subordinate and manager Position anchors must be visible and the union of same-tenant `active`/`open` `position_record_version` effective ranges must cover the relationship's entire effective interval. PostgreSQL `range_agg(daterange(...))` produces a normalized date multirange, and multirange containment proves full coverage without enumerating days or incorrectly rejecting legitimate contiguous active/open Position versions. A stable Position record without staffable bitemporal PositionVersion coverage is therefore insufficient persistence evidence.

Graph acyclicity is tenant-wide and cannot be protected by independent row constraints alone. Before a version trigger reads the graph, it obtains a transaction-scoped PostgreSQL advisory lock keyed from the tenant UUID. Opposite concurrent mutations for one tenant are therefore serialized, while different tenants can proceed independently. The PL/pgSQL trigger remains the default `VOLATILE`; PostgreSQL documents that a `VOLATILE` function obtains a fresh snapshot for each SQL query it executes. After a waiting transaction acquires the tenant graph lock, its recursive graph query therefore sees the relationship committed by the preceding lock holder and rejects the opposite edge as a cycle. Hash-key collisions can only over-serialize unrelated tenants; they cannot relax the invariant.

## Why this shape

The anchor/version split keeps stable relationship identity separate from changing manager/effective-time facts and therefore remains 3NF while supporting bitemporal correction. PostgreSQL exclusion/range semantics prevent overlapping business/system versions under one relationship identity; the insert guard performs cross-row cycle validation that a row-local `CHECK` constraint cannot express. RLS is defense in depth rather than authorization by itself: the application role must remain `NOSUPERUSER NOBYPASSRLS`, and high-level mutation authority remains outside this migration.

The staffable coverage check deliberately validates the full reporting interval rather than only its start date. Otherwise a relationship could be stored as authoritative while one endpoint has no active/open PositionVersion for later days that the relationship itself claims to cover. The database check therefore matches the descriptive snapshot semantics instead of relying on downstream readers to discover and reject internally inconsistent persisted truth.

The audit binding deliberately uses the already immutable `audit_event_record` envelope as the application evidence instead of trusting an unrelated caller-provided digest. The event identifies the applying actor, tenant, relationship subject, governed purpose and reason, result, time, and reviewed-evidence digest; storing its exact envelope digest makes the relationship version cryptographically correlate to that immutable application fact.

The tenant advisory lock is intentionally narrow: it protects only graph mutation validation and is transaction-scoped. It does not replace transaction boundaries, RLS, authorization, or history guards. Its purpose is to make cycle validation defensible under concurrent writes rather than merely correct in single-session tests.

## Integration and stack boundary

This PR is a Draft descendant of #94 and cannot inherit #94 checks or reviews. It must not merge before #94. After #94 is integrated, retarget #106 to the fresh protected `develop`, reconcile any migration-number/document conflicts, and re-run full exact-head CI/security/recovery evidence.

PR #95 owns the in-memory pre-mutation review packet. This persistence slice does not copy or modify that branch; it accepts the review digest plus immutable application audit evidence as the handoff boundary. A later authorized host adapter may translate a verified review packet into the database command, but direct cross-service SQL is out of scope.

Canonical `docs/DATA_MODEL.md` / `docs/ERD.md` now record the proposed active-PR relationship tables and explicitly distinguish them from protected-main truth. Integration must reconcile the accepted relationship tables and remove the active-PR qualification after dependency ordering is resolved.

## Consequences

The database can preserve audited supervisory hierarchy truth independently of current worker occupancy. Reads can combine persisted relationships with PR #94's staffable-Position snapshot semantics, and persistence now rejects an edge whose PositionVersion evidence cannot support every day that the edge claims to cover. The stricter model rejects ambiguous duplicate anchors, self-reporting, single-session and concurrent cycles, caller-backdated system time, mutation of history, tenant-crossing references, non-staffable endpoint coverage, and audit evidence whose governed reason does not match the reviewed reporting-line application rather than silently repairing them.

This ADR does not claim certification, branch-protection enforcement, release readiness, or authorization to make employment decisions.
