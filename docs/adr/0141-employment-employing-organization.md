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

At any single effective-date/system-recorded-time coordinate, one Employment may resolve to at most one employing organization. The organization must be classified as `legal_entity` across the relationship's full effective interval at the relationship's recorded-time coordinate. The relationship interval must also be fully covered by `active` or `leave` Employment truth at that same recorded-time coordinate.

The relationship is independent of Position and Assignment. It stores no Person PII, compensation, payroll, tax, benefits, statutory-account, candidate, performance, or model-output fields.

History is correction-not-rewrite: business fields cannot be updated in place; the current recorded interval may only be closed and a replacement fact inserted. DELETE and TRUNCATE are rejected. Tenant-qualified foreign keys and forced RLS independently protect cross-tenant integrity and visibility.

## Consequences

- Workforce and employment-contract scope can distinguish legal employer from seat/organization placement.
- Position transfers do not silently rewrite employer identity.
- Legal-employer corrections preserve what Orgmetra knew and when.
- The model remains usable without payroll or statutory-account ownership.
- A future mutation API must add purpose-bound authorization, accountable actor/reason/evidence, immutable audit/outbox, and idempotency; this persistence slice alone does not authorize a high-impact Employment change.

## Alternatives rejected

1. **Infer employer from Position.organization_unit_id.** Rejected because seat ownership and legal employment are different facts and can change independently.
2. **Store employer directly on `employment_record`.** Rejected because it would erase effective/system history and conflate durable Employment identity with a mutable relationship.
3. **Store a free-text legal-employer code.** Rejected because it breaks tenant-qualified Organization integrity and workforce lineage.
4. **Add payroll/legal-accounting tables.** Rejected as outside this bounded HRIS slice and outside accepted owner contracts.

## Verification

`tests/test_employment_employing_organization_postgres.sh` proves:

- one employer per Employment business/system coordinate;
- full-interval `legal_entity` classification;
- full-interval active/leave Employment coverage;
- tenant-qualified cross-tenant rejection;
- correction-not-rewrite history;
- TRUNCATE protection; and
- forced-RLS isolation under a `NOSUPERUSER NOBYPASSRLS` application role.

## References

International Organization for Standardization. (2025). *ISO 30414:2025 Human resource management — Requirements and recommendations for human capital reporting and disclosure* (2nd ed.). ISO.
