# ADR-0141: Employment employing-organization truth

- Status: proposed_on_active_pr
- Date: 2026-08-28
- Owner: Orgmetra HRIS core
- Scope: Employment / Organization

## Context

Protected `develop` models Person, Employment, Organization, Job, Position, and Assignment as distinct concepts, but Employment itself has no authoritative link to the organization that is the legal employer. Inferring legal employer from Position is unsafe: a Position move need not change the employing legal entity, and a legal-employer transfer need not imply the same Position semantics.

For commercial HRIS use, the employer relationship must therefore be a first-class temporal HR fact, not a denormalized Position attribute or an application-only lookup.

ISO 30414:2025 is the current published second edition of the human-capital reporting/disclosure standard and includes workforce composition among its core reporting areas. That supports the need for defensible organizational scope in workforce reporting; it does **not** prescribe this schema or authorize statutory/payroll interpretation.

## Decision

Add `employment_employing_organization_record` as a 3NF bitemporal relationship between one tenant-scoped Employment and one tenant-scoped Organization.

At every effective-date/system-recorded-time coordinate where Employment status is `active` or `leave`, exactly one employing organization must resolve: overlaps are rejected by the bitemporal exclusion and missing relationships or effective gaps are rejected by deferred database constraint triggers. The organization must be classified as `legal_entity` across the relationship's full effective interval at the relationship's recorded-time coordinate. The relationship interval must also be fully covered by `active` or `leave` Employment truth at that same recorded-time coordinate.

Because the exact-one rule spans Employment versions, employer relationships, and Organization versions, deferred validation alone is insufficient under `READ COMMITTED`: two concurrent transactions can otherwise validate snapshots that exclude each other's uncommitted changes. Before a mutation that can affect the invariant proceeds, Orgmetra therefore takes one tenant-scoped transaction advisory lock for active/leave Employment version changes, every employer-relationship mutation, and legal-entity or already-referenced Organization-version changes. The lock serializes only the integrity-changing transaction class; deferred triggers still perform the authoritative cross-table validation at commit after any competing transaction becomes visible. The lock is an integrity mechanism, not an authorization mechanism, and a hash collision may only add harmless serialization rather than permit invalid state.

The relationship is independent of Position and Assignment. It stores no Person PII, compensation, payroll, tax, benefits, statutory-account, candidate, performance, or model-output fields.

The API compatibility boundary is explicit. Existing `/v1` Employment and confirmed-hire payloads remain available for legacy terminated writes, while an active or leave `/v1` payload without employer facts fails before persistence with migration guidance. Employer-required writes use `/v2`; this keeps the exact-one database invariant intact without silently inventing a legal employer or changing the meaning of an existing V1 request.

History is correction-not-rewrite: business fields cannot be updated in place; the current recorded interval may only be closed and a replacement fact inserted. DELETE and TRUNCATE are rejected. Tenant-qualified foreign keys and forced RLS independently protect cross-tenant integrity and visibility.

## Consequences

- Workforce and employment-contract scope can distinguish legal employer from seat/organization placement.
- Position transfers do not silently rewrite employer identity.
- Legal-employer corrections preserve what Orgmetra knew and when.
- Concurrent employer-classification, relationship, and active/leave Employment mutations for one tenant serialize before exact-one validation, preventing READ COMMITTED write skew.
- Tenant-local bulk Employment/employer migrations must account for this integrity lock in batching and lock-wait observability; any future reduction in lock granularity must preserve the concurrency regression before adoption.
- The model remains usable without payroll or statutory-account ownership.
- Mutation APIs additionally require purpose-bound authorization, accountable actor/reason/evidence, immutable audit/outbox, and idempotency; persistence integrity alone does not authorize a high-impact Employment change.

## Alternatives rejected

1. **Infer employer from Position.organization_unit_id.** Rejected because seat ownership and legal employment are different facts and can change independently.
2. **Store employer directly on `employment_record`.** Rejected because it would erase effective/system history and conflate durable Employment identity with a mutable relationship.
3. **Store a free-text legal-employer code.** Rejected because it breaks tenant-qualified Organization integrity and workforce lineage.
4. **Rely on deferred cross-table triggers without write serialization.** Rejected because concurrent `READ COMMITTED` transactions can validate before either commit becomes visible and leave a write-skewed final state.
5. **Add payroll/legal-accounting tables.** Rejected as outside this bounded HRIS slice and outside accepted owner contracts.

## Verification

`tests/test_employment_employing_organization_postgres.sh` proves:

- exactly one employer per active/leave Employment business/system coordinate, including missing and effective-gap rejection;
- full-interval `legal_entity` classification;
- full-interval active/leave Employment coverage;
- deterministic serialization of a legal-entity reclassification against a competing active Employment/employer write before deferred validation;
- tenant-qualified cross-tenant rejection;
- correction-not-rewrite history;
- TRUNCATE protection; and
- forced-RLS isolation under a `NOSUPERUSER NOBYPASSRLS` application role.

## References

International Organization for Standardization. (2025). *ISO 30414:2025 Human resource management — Requirements and recommendations for human capital reporting and disclosure* (2nd ed.). ISO.
