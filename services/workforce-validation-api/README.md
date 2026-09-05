# Orgmetra Workforce Validation API

This package is the application boundary for the `workforce_validation` bounded context. The current slice exposes one purpose-bound read use case for the existing validity-study registry header and establishes the context-local PostgreSQL ownership bootstrap.

It does **not** query People, Talent Acquisition, Performance Management, Job Architecture, Psychometrics Commons, fast-mlsirm, or TEPP tables. Those contexts remain separate owners. Exact foreign identifiers and immutable specialist result references cross the boundary only through published contracts.

## Current slice

`read_validity_study(...)`:

- accepts structurally immutable authenticated Keyverse identity attributes, not credentials;
- reconstructs and revalidates principal storage before building the access request, so exact tuple type alone is not treated as identity authority;
- stores UUID identity evidence behind the tuple-backed principal/record/view as exact integer payloads and reconstructs fresh UUID objects at public boundaries, so a retained UUID reference cannot rewrite accepted tenant/study/criterion identity through `object.__setattr__`;
- preserves tenant/study authorization targets as immutable integer snapshots across the executable repository call, so a repository cannot make a foreign record self-consistent by mutating the UUID objects it receives;
- inertly verifies that the owner repository exposes a statically callable `read_validity_study` capability before authorization, without executing caller-controlled descriptors;
- evaluates tenant, purpose, operation, scope, resource, and requested fields before persistence;
- calls only a `ValidityStudyReadPort` owned by this context;
- reconstructs persisted registry scalars into structurally immutable owner evidence before target validation and output;
- returns only the fields authorized for the exact study record; UUID-valued projected fields are reconstituted fresh rather than exposing mutable internal UUID aliases;
- issues `ValidityStudyView` only from the authorized read path. Its public constructor fails closed, and the returned tuple-backed projection cannot be rewritten through ordinary assignment or `object.__setattr__`.

`ValidityStudyView` is a data projection, not a durable authorization credential or cryptographic capability. Downstream consequential actions must perform their own purpose-bound authorization and authoritative re-resolution rather than treating the Python runtime type as reusable authority. Low-level interpreter construction is outside the supported public API and is not accepted as proof that authorization occurred.

`services/workforce-validation-api/database/migrations/0001_owner_schema.sql` starts this bounded context's own migration history. It creates the `workforce_validation` schema and deny-default `workforce_validation_role`, revokes public schema access, and intentionally creates or moves no application table yet. The role is a **NOLOGIN migration/schema owner only**; runtime principals must not be granted that owner role. PostgreSQL applies role-level configuration defaults at login and does not re-apply them on `SET ROLE`, so an `ALTER ROLE ... SET search_path` entry on this NOLOGIN role is not treated as a runtime isolation control. The later durable adapter must use a distinct least-privilege runtime role, schema-qualified `workforce_validation` relations, and explicit function-level `search_path` where `SECURITY DEFINER` code is introduced.

Protected foundation migrations still create validity-study tables in the legacy foundation schema, so the next forward-only persistence increment must adopt those records without normalizing `public.validity_study` as a long-lived service contract or breaking existing linkage evidence.

Issue #234 owns the remaining order: durable owner-schema adoption and PostgreSQL adapter, idempotent registration, explicit predictor/sample/decision-policy/analysis-protocol versions, scientific adapters, OpenAPI/gateway exposure, and realistic p95 measurement. Issues #236–#243 retain the current bootstrap trust-boundary findings through exact-head acceptance and protected integration: persisted-record immutability, principal immutability and constructor revalidation, owner-role/runtime-role separation, inert repository-capability validation, immutable minimized output, non-public issuance of that output, and detached UUID storage/target snapshots.

## Test

The Draft branch is admitted to the canonical Foundation quality workflow with the same hash-locked test toolchain and direct source-tree dependency policy used by the existing owner services:

```bash
PYTHONPATH=services/workforce-validation-api/src:packages/keyverse-adapter/src \
  COVERAGE_FILE=/tmp/orgmetra-workforce-validation-api.coverage \
  python -m pytest -c services/workforce-validation-api/pyproject.toml \
  services/workforce-validation-api/tests
```

The same Foundation job also runs `tests/test_workforce_validation_owner_schema_postgres.sh` in its own pinned PostgreSQL 16.14 container. That contract executes the service-local owner migration and checks the exact deny-default role flags, schema owner, absence of ineffective login-only `rolconfig`, actual `SET ROLE` search-path behavior, absence of inherited PUBLIC `USAGE`/`CREATE`, and absence of application relations in the bootstrap schema. The test intentionally demonstrates that `SET ROLE` retains the caller's existing `search_path`; runtime isolation therefore cannot be inferred from owner-role metadata.

Those source contracts are not terminal acceptance by themselves. The slice remains Draft until the exact current head actually executes with 100% owned statement/branch coverage, the PostgreSQL owner-schema contract is GREEN, applicable security workflows are terminal, and the normal review/governance requirements are satisfied. Only then may the next forward-only owner-table adoption and durable adapter be treated as eligible for integration.
