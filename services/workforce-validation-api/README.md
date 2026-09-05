# Orgmetra Workforce Validation API

This package is the application boundary for the `workforce_validation` bounded context. The current slice exposes one purpose-bound read use case for the existing validity-study registry header and establishes the context-local PostgreSQL ownership bootstrap.

It does **not** query People, Talent Acquisition, Performance Management, Job Architecture, Psychometrics Commons, fast-mlsirm, or TEPP tables. Those contexts remain separate owners. Exact foreign identifiers and immutable specialist result references cross the boundary only through published contracts.

## Current slice

`read_validity_study(...)`:

- accepts structurally immutable authenticated Keyverse identity attributes, not credentials;
- evaluates tenant, purpose, operation, scope, resource, and requested fields before persistence;
- calls only a `ValidityStudyReadPort` owned by this context;
- reconstructs persisted registry scalars into structurally immutable owner evidence before target validation and output;
- returns only the fields authorized for the exact study record.

`services/workforce-validation-api/database/migrations/0001_owner_schema.sql` starts this bounded context's own migration history. It creates the `workforce_validation` schema and `workforce_validation_role`, revokes public schema access, and limits the role's default search path to the owner schema plus `pg_catalog`. It intentionally creates or moves no application table yet. Protected foundation migrations still create validity-study tables in the legacy foundation schema, so the next forward-only persistence increment must adopt those records without normalizing `public.validity_study` as a long-lived service contract or breaking existing linkage evidence.

Issue #234 owns the remaining order: PostgreSQL-backed owner-schema acceptance and durable adapter, idempotent registration, explicit predictor/sample/decision-policy/analysis-protocol versions, scientific adapters, OpenAPI/gateway exposure, and realistic p95 measurement. Issue #237 separately tracks the authenticated-principal structural-immutability repair until exact-head acceptance and protected integration.

## Test

The Draft branch is admitted to the canonical Foundation quality workflow with the same hash-locked test toolchain and direct source-tree dependency policy used by the existing owner services:

```bash
PYTHONPATH=services/workforce-validation-api/src:packages/keyverse-adapter/src \
  COVERAGE_FILE=/tmp/orgmetra-workforce-validation-api.coverage \
  python -m pytest -c services/workforce-validation-api/pyproject.toml \
  services/workforce-validation-api/tests
```

The package declares 100% owned statement and branch coverage. The current test suite also seals the location and deny-default shape of the bounded-context-local owner-schema migration. Source-level workflow admission and static migration contract are not PostgreSQL acceptance evidence by themselves: this slice remains Draft until the exact current head has terminal owner coverage, required security/review evidence, and a PostgreSQL-backed owner-schema contract before any durable adapter is treated as production-ready.
