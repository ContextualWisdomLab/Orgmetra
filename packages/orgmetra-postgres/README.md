# orgmetra-postgres

`orgmetra-postgres` is the independently importable PostgreSQL adapter for the
Orgmetra HRIS core. It enforces tenant context at the database transaction
boundary and writes non-content audit evidence in the same transaction as each
accepted HR mutation.

The package does not own HTTP routing, authentication, credentials, queues,
LLM execution, psychometric computation, or deployment. A host authenticates the
caller and constructs a `PurposeContext`; this adapter binds that context to the
transaction and the database row-level-security policy.

## Initial vertical slice

- create a tenant record
- create and read a person record
- create and read an employment record
- create and read a candidate profile
- link a candidate to one worker idempotently and read that hire link
- write purpose-bound audit evidence atomically
- deny cross-tenant reads through PostgreSQL RLS

The initial migration is pre-GA and assumes an empty foundation database. A
future accepted migration contract must add upgrade and rollback handling before
production deployment.
