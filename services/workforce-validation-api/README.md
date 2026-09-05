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

Issue #234 owns the remaining order: durable owner-schema adoption and PostgreSQL adapter, idempotent registration, explicit predictor/sample/decision-policy/analysis-protocol versions, scientific adapters, OpenAPI/gateway exposure, and realistic p95 measurement. Issue #237 separately tracks the authenticated-principal structural-immutability repair until exact-head acceptance and protected integration.

## Test

The Draft branch is admitted to the canonical Foundation quality workflow with the same hash-locked test toolchain and direct source-tree dependency policy used by the existing owner services:

```bash
PYTHONPATH=services/workforce-validation-api/src:packages/keyverse-adapter/src \
  COVERAGE_FILE=/tmp/orgmetra-workforce-validation-api.coverage \
  python -m pytest -c services/workforce-validation-api/pyproject.toml \
  services/workforce-validation-api/tests
```

The same Foundation job now also runs `tests/test_workforce_validation_owner_schema_postgres.sh` in its own pinned PostgreSQL 16.14 container. That contract executes the service-local owner migration and checks the exact role flags, schema owner, role search path, absence of inherited PUBLIC `USAGE`/`CREATE`, and absence of application relations in the bootstrap schema. The workflow manifest is resealed after admitting this contract.

Those source contracts are not terminal acceptance by themselves. The slice remains Draft until the exact current head actually executes with 100% owned statement/branch coverage, the PostgreSQL owner-schema contract is GREEN, applicable security workflows are terminal, and the normal review/governance requirements are satisfied. Only then may the next forward-only owner-table adoption and durable adapter be treated as eligible for integration.
