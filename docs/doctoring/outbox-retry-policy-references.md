# Outbox retry policy references

This note records primary technical sources used for the active governed outbox retry-policy design. It is evidence for design review, not a certification claim.

## Design implications

PostgreSQL row-level security is the authoritative tenant-isolation mechanism for the policy relation. FORCE RLS is paired with tests under a `NOBYPASSRLS` role because table owners, superusers, and roles with `BYPASSRLS` can otherwise bypass ordinary row-security enforcement depending on execution context.

The retry delay uses bounded exponential growth and a maximum delay. Google Cloud's retry guidance recommends truncated exponential backoff with jitter for failed requests. This PR intentionally implements the durable policy and capped exponential component only; jitter remains a separate planned transport/scheduling concern and must not be inferred from the current implementation.

The retry-policy `recorded_from` and `recorded_to` values are system-recorded evidence rather than caller-authored business time. PostgreSQL documents `transaction_timestamp()` as the start time of the current transaction and keeps that value stable for the transaction, which provides one database-controlled recorded instant for policy writes and interval closure. The active PR therefore rejects a caller-supplied `recorded_from`, requires a new policy interval to begin open, and requires closure at the current transaction time rather than accepting a forged historical `recorded_to`. This does not collapse business/effective time into system-recorded time; the two temporal meanings remain separate.

## APA 7 references

Google Cloud. (2026, August 13). *Retry failed requests*. Google Cloud IAM Documentation. https://cloud.google.com/iam/docs/retry-strategy

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: CREATE POLICY*. https://www.postgresql.org/docs/16/sql-createpolicy.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Client connection defaults and role attributes*. https://www.postgresql.org/docs/16/runtime-config-client.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Date/time functions and operators*. https://www.postgresql.org/docs/16/functions-datetime.html
