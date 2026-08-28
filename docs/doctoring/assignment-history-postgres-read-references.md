# PostgreSQL Assignment-history read references

Status: active stacked-PR research evidence for ADR 0148. These sources support transaction and row-security design decisions; they do not establish PostgreSQL, security, privacy, SOC 2, CSAP, or other certification for Orgmetra.

## APA 7 references

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: SET TRANSACTION*. https://www.postgresql.org/docs/18/sql-set-transaction.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: ALTER TABLE*. https://www.postgresql.org/docs/18/sql-altertable.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Row security policies*. https://www.postgresql.org/docs/18/ddl-rowsecurity.html

## Applied boundary

- `SET TRANSACTION ... READ ONLY` is used as a database-side guard against ordinary data-changing statements during Assignment-history reads. The adapter performs one scoped SELECT, so `READ COMMITTED` provides the needed statement snapshot without claiming serializable business semantics.
- Existing Orgmetra database migrations own row-level-security enablement, FORCE RLS, and tenant policies. The adapter sets the transaction-local tenant context before querying and also uses explicit tenant/person predicates; neither mechanism is treated as a substitute for the parent People service's purpose-bound authorization.
- `FORCE ROW LEVEL SECURITY` is relevant because PostgreSQL otherwise permits table owners to bypass their own row policies. ADR 0148 consumes the existing hardened database contract rather than altering policy ownership in this slice.
- The references do not authorize disclosure of Assignment fields. Exact field disclosure remains governed by PR #142's purpose-bound Keyverse authorization contract.

## Review date

Rechecked against the PostgreSQL 18 official documentation on 2026-08-29. Re-review if a later final major version materially changes read-only transaction or row-security behavior used by this adapter.
