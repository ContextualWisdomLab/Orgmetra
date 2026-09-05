# Orgmetra Workforce Validation API

This package is the application boundary for the `workforce_validation` bounded context. The first slice exposes one purpose-bound read use case for the existing validity-study registry header.

It does **not** query People, Talent Acquisition, Performance Management, Job Architecture, Psychometrics Commons, fast-mlsirm, or TEPP tables. Those contexts remain separate owners. Exact foreign identifiers and immutable specialist result references cross the boundary only through published contracts.

## Current slice

`read_validity_study(...)`:

- accepts authenticated Keyverse identity attributes, not credentials;
- evaluates tenant, purpose, operation, scope, resource, and requested fields before persistence;
- calls only a `ValidityStudyReadPort` owned by this context;
- reconstructs persisted registry scalars into structurally immutable owner evidence before target validation and output;
- returns only the fields authorized for the exact study record.

The repository port is intentionally abstract in this increment. Protected foundation migrations still create the validity-study tables in the legacy foundation schema while `ARCHITECTURE.md` assigns them to the `workforce_validation` schema and database role. A direct `public.validity_study` adapter here would turn that implementation drift into a new long-lived service contract.

Issue #234 owns the next order: service-owned schema/role, durable PostgreSQL adapter, idempotent registration, explicit predictor/sample/decision-policy/analysis-protocol versions, scientific adapters, OpenAPI/gateway exposure, and realistic p95 measurement.

## Test

The Draft branch is admitted to the canonical Foundation quality workflow with the same hash-locked test toolchain and direct source-tree dependency policy used by the existing owner services:

```bash
PYTHONPATH=services/workforce-validation-api/src:packages/keyverse-adapter/src \
  COVERAGE_FILE=/tmp/orgmetra-workforce-validation-api.coverage \
  python -m pytest -c services/workforce-validation-api/pyproject.toml \
  services/workforce-validation-api/tests
```

The package declares 100% owned statement and branch coverage. Source-level workflow admission is not acceptance evidence by itself: this slice remains Draft until that command and the repository gates are terminal GREEN on the exact current head and qualifying independent review is satisfied.
