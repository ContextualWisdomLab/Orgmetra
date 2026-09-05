# Orgmetra Workforce Validation API

This package is the application and persistence boundary for the `workforce_validation` bounded context. The current stack exposes a purpose-bound validity-study registry read and adopts the existing registry table into the context-owned PostgreSQL schema without copying authoritative HR evidence.

It does **not** query People, Talent Acquisition, Performance Management, Job Architecture, Psychometrics Commons, fast-mlsirm, or TEPP tables. Those contexts remain separate owners. Exact foreign identifiers and immutable specialist result references cross the boundary only through published contracts or explicitly approved database constraints inside the modular deployment.

## Current read boundary

`read_validity_study(...)`:

- accepts structurally immutable authenticated Keyverse identity attributes, not credentials;
- reconstructs and revalidates principal storage before building the access request, so exact tuple type alone is not treated as identity authority;
- requires both exact `UUID` outer type and exact built-in integer UUID payload before any sentinel/range comparison, so a forged exact UUID with executable internal storage is rejected without invoking caller-defined equality behavior;
- stores UUID identity evidence behind the tuple-backed principal/record/view as exact integer payloads and reconstructs fresh UUID objects at public boundaries, so a retained UUID reference cannot rewrite accepted tenant/study/criterion identity through `object.__setattr__`;
- preserves tenant/study authorization targets as immutable integer snapshots across the executable repository call, so a repository cannot make a foreign record self-consistent by mutating the UUID objects it receives;
- inertly verifies that the owner repository exposes a statically callable `read_validity_study` capability before authorization, without executing caller-controlled descriptors;
- evaluates tenant, purpose, operation, scope, resource, and requested fields before persistence;
- calls only a `ValidityStudyReadPort` owned by this context;
- reconstructs persisted registry scalars into structurally immutable owner evidence before target validation and output;
- returns only the fields authorized for the exact study record; UUID-valued projected fields are reconstituted fresh rather than exposing mutable internal UUID aliases;
- issues `ValidityStudyView` only from the authorized read path. Its public constructor fails closed, and the returned tuple-backed projection cannot be rewritten through ordinary assignment or `object.__setattr__`.

`ValidityStudyView` is a data projection, not a durable authorization credential or cryptographic capability. Downstream consequential actions must perform their own purpose-bound authorization and authoritative re-resolution rather than treating the Python runtime type as reusable authority. Low-level interpreter construction is outside the supported public API and is not accepted as proof that authorization occurred.

## PostgreSQL ownership

`database/migrations/0001_owner_schema.sql` creates the deny-default `workforce_validation` schema and `workforce_validation_role`. That role remains a **NOLOGIN migration/schema owner only**; runtime principals must not be granted it. PostgreSQL role-level configuration defaults are not treated as runtime isolation because `SET ROLE` does not re-apply login-time defaults.

`database/migrations/0002_registry_adoption.sql` is a forward-only adoption migration. It uses `ALTER TABLE public.validity_study SET SCHEMA workforce_validation`, so the existing relation OID, rows, indexes, foreign-key dependencies, forced tenant RLS policy, and bitemporal mutation trigger stay attached to the same table object. It creates a separate deny-default `workforce_validation_runtime_role`, grants only schema `USAGE`, registry `SELECT`, and the tenant-context helper required by the preserved RLS policy, and grants no registry mutation privilege. No `public.validity_study` compatibility view or second mutable registry is created.

`PostgresValidityStudyReadPort` uses only `workforce_validation.validity_study` and `pg_catalog.set_config(...)`. It snapshots tenant/study UUID authority into immutable integer payloads before executable connection acquisition, reconstructs fresh UUID parameters, opens a read-only transaction, binds `orgmetra.tenant_record_id` transaction-locally, fetches at most two rows, and fails closed on duplicate, malformed, non-canonical, or foreign-target persistence results. Deployment code owns the actual login, pooling, TLS and assumption/grant of the runtime role; the adapter does not elevate itself with `SET ROLE`.

The legacy decision/evidence/outcome links remain separate relations for now. Their existing foreign keys continue to reference the moved registry by relation identity, which PostgreSQL preserves across `SET SCHEMA`. Later increments must adopt the remaining `workforce_validation` relations deliberately rather than create cross-service SQL or duplicate the registry.

Issue #234 owns the broader FR-007 order. Issue #247 owns this durable registry adoption/read-port slice. After its exact-head acceptance and the parent #235 protected integration, the next buyer/scientific work is idempotent validity-study registration, explicit predictor/sample/decision-policy/analysis-protocol versions, scientific adapters, versioned OpenAPI/gateway exposure, and realistic PostgreSQL-backed p95 evidence.

## Test

The service remains in the canonical Foundation unit gate with the repository's hash-locked test toolchain:

```bash
PYTHONPATH=services/workforce-validation-api/src:packages/keyverse-adapter/src \
  COVERAGE_FILE=/tmp/orgmetra-workforce-validation-api.coverage \
  python -m pytest -c services/workforce-validation-api/pyproject.toml \
  services/workforce-validation-api/tests
```

`tests/test_workforce_validation_owner_schema_postgres.sh`, already admitted to the pinned PostgreSQL 16.14 Foundation lane, first proves the empty owner-schema bootstrap and then applies the foundation schema plus `0002_registry_adoption.sql`. It verifies preserved relation OID/FK dependencies/RLS/bitemporal guard, absence of `public.validity_study`, deny-default runtime-role flags, read-only privileges, no-row behavior without tenant context, and tenant-scoped owner reads.

Source contracts are not terminal acceptance by themselves. This child remains Draft while #235 is mutable and until, after parent integration/retarget, its exact head executes with 100% owned statement/branch coverage, the isolated PostgreSQL contract is GREEN, applicable security workflows are terminal, and normal review/governance requirements are satisfied.
