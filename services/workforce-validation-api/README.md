# Orgmetra Workforce Validation API

This package is the application boundary for the `workforce_validation` bounded context. The first slice exposes one purpose-bound read use case for the existing validity-study registry header.

It does **not** query People, Talent Acquisition, Performance Management, Job Architecture, Psychometrics Commons, fast-mlsirm, or TEPP tables. Those contexts remain separate owners. Exact foreign identifiers and immutable specialist result references cross the boundary only through published contracts.

## Current slice

`read_validity_study(...)`:

- accepts authenticated Keyverse identity attributes, not credentials;
- evaluates tenant, purpose, operation, scope, resource, and requested fields before persistence;
- calls only a `ValidityStudyReadPort` owned by this context;
- reconstructs and validates durable registry scalars before returning them;
- returns only the fields authorized for the exact study record.

The repository port is intentionally abstract in this increment. Protected foundation migrations still create the validity-study tables in the legacy foundation schema while `ARCHITECTURE.md` assigns them to the `workforce_validation` schema and database role. A direct `public.validity_study` adapter here would turn that implementation drift into a new long-lived service contract.

Issue #234 owns the next order: service-owned schema/role, durable PostgreSQL adapter, idempotent registration, explicit predictor/sample/decision-policy/analysis-protocol versions, scientific adapters, OpenAPI/gateway exposure, and realistic p95 measurement.

## Test

Once this service is admitted to Foundation CI, its contract is:

```bash
PYTHONPATH=services/workforce-validation-api/src:packages/keyverse-adapter/src \
  python -m pytest -c services/workforce-validation-api/pyproject.toml \
  services/workforce-validation-api/tests
```

The package declares 100% owned statement and branch coverage. Until the repository-wide Foundation writer includes this command and the exact head is GREEN, this slice remains Draft evidence rather than shipped product truth.
