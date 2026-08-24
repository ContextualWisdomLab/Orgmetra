# ADR 0106 — Bitemporal Position reporting persistence

- **Status:** Proposed in active PR #106; not protected-main truth
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

A version insert fails closed unless it has an open same-tenant anchor, a different reviewer and applying actor, immutable same-tenant audit/outbox evidence for `position_reporting_change_apply`, no self-reporting edge, and no management cycle over an overlapping effective period. The application audit event must carry the exact reviewed-evidence digest in `orgmetraevidence`; the version's application-evidence digest must equal the persisted audit envelope digest. This prevents a syntactically valid reviewer/digest pair from being recorded without immutable evidence binding. Composite foreign keys bind both subordinate and manager Position IDs to the same tenant.

## Why this shape

The anchor/version split keeps stable relationship identity separate from changing manager/effective-time facts and therefore remains 3NF while supporting bitemporal correction. PostgreSQL exclusion/range semantics prevent overlapping business/system versions under one relationship identity; the insert guard performs cross-row cycle validation that a row-local `CHECK` constraint cannot express. RLS is defense in depth rather than authorization by itself: the application role must remain `NOSUPERUSER NOBYPASSRLS`, and high-level mutation authority remains outside this migration.

The audit binding deliberately uses the already immutable `audit_event_record` envelope as the application evidence instead of trusting an unrelated caller-provided digest. The event identifies the applying actor, tenant, relationship subject, purpose, result, time, and reviewed-evidence digest; storing its exact envelope digest makes the relationship version cryptographically correlate to that immutable application fact.

## Integration and stack boundary

This PR is a Draft descendant of #94 and cannot inherit #94 checks or reviews. It must not merge before #94. After #94 is integrated, retarget #106 to the fresh protected `develop`, reconcile any migration-number/document conflicts, and re-run full exact-head CI/security/recovery evidence.

PR #95 owns the in-memory pre-mutation review packet. This persistence slice does not copy or modify that branch; it accepts the review digest plus immutable application audit evidence as the handoff boundary. A later authorized host adapter may translate a verified review packet into the database command, but direct cross-service SQL is out of scope.

Canonical `docs/DATA_MODEL.md` / `docs/ERD.md` are intentionally not edited in this stacked slice while independent active database PRs also own those high-conflict documents. Integration must reconcile the accepted relationship tables into canonical data-model documentation after dependency ordering is resolved.

## Consequences

The database can preserve audited supervisory hierarchy truth independently of current worker occupancy. Reads can combine persisted relationships with PR #94's staffable-Position snapshot semantics. The stricter model rejects ambiguous duplicate anchors, self-reporting, cycles, caller-backdated system time, mutation of history, tenant-crossing references, and unbound review/application evidence rather than silently repairing them.

This ADR does not claim certification, branch-protection enforcement, release readiness, or authorization to make employment decisions.
