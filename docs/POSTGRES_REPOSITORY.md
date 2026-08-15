# PostgreSQL repository contract

## Customer outcome

A customer can store the first Orgmetra people and candidate records in a
shared PostgreSQL deployment without exposing one tenant's rows to another and
without losing the audit evidence that explains an accepted mutation.

## Host responsibilities

Before calling the repository, the host must:

1. authenticate the user or service;
2. authorize the requested purpose and resource scope;
3. construct a `PurposeContext` using opaque tenant, actor, correlation and
   decision references;
4. obtain the DSN from a secret manager;
5. use a `NOSUPERUSER NOBYPASSRLS` application role;
6. keep database credentials, names and free-text HR content out of logs.

The repository never accepts an untrusted request header as tenant authority.

## Data behavior

- Tenant context is transaction-local and therefore safe for transaction-pool
  reuse when the pool returns a clean transaction boundary.
- Forced row-level security denies reads when tenant context is absent.
- Composite tenant relationships refuse cross-tenant references.
- Accepted mutations and their audit evidence commit or roll back together.
- Candidate-to-worker linkage is idempotent for the same identity and refuses a
  conflicting worker identity.
- Audit payloads contain references and action metadata, not names, documents or
  assessment responses.

## Migration boundary

`0002_tenant_audit_boundary.sql` is a pre-GA fresh-database migration. It assumes
that the foundation tables contain no production rows. Before any populated
upgrade, Orgmetra needs a separate expand/backfill/validate/contract migration,
rollback rehearsal and customer-visible maintenance procedure.

## Local verification

```bash
export ORGMETRA_TEST_ADMIN_DATABASE_URL='postgresql://postgres:password@127.0.0.1:5432/orgmetra_test'
export PYTHONPATH='packages/orgmetra-postgres/src'
python -m pip install --only-binary=:all: --require-hashes -r requirements/postgres-ci.txt
python -m coverage run --branch --source=orgmetra_postgres -m pytest packages/orgmetra-postgres/tests
python -m coverage report --show-missing --fail-under=100
python packages/orgmetra-postgres/tests/validate_docstrings.py
```

The integration suite recreates the `public` schema. Run it only against an
isolated disposable database.

## Production gaps before release

- digest-pinned PostgreSQL test images;
- populated-database migration and rollback;
- connection-pool integration and recovery tests;
- backup, restore and point-in-time recovery evidence;
- encryption and key-management deployment profile;
- complete people/employment/position/assignment repository surface;
- OpenTelemetry metrics that contain no HR content;
- external penetration and procurement review.
