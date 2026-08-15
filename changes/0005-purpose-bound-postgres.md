# Unreleased: purpose-bound PostgreSQL persistence

## Added

- tenant-scoped `orgmetra-postgres` adapter
- same-transaction non-content audit evidence
- forced PostgreSQL row-level security
- cross-tenant relationship constraints
- append-only high-impact decision and observation facts
- real PostgreSQL 17/18 integration test matrix

## Security

- tenant context is bound with a transaction-local database setting
- application roles require `NOSUPERUSER NOBYPASSRLS`
- missing tenant context denies protected rows
- raw SQL, credentials and HR content are excluded from repository errors and
  audit payloads

## Known limits

This is a pre-GA fresh-database slice. Populated-database migration, image digest
pinning, backup/restore and the complete HRIS repository surface are not yet
release-ready.
