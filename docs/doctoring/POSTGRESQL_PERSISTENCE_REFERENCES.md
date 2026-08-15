# PostgreSQL persistence references

This doctoring note records the standards and primary technical sources used by
ADR-0005 and the first purpose-bound persistence slice. Product claims must stay
within the implemented and tested boundary; these references do not establish
certification.

## Decision traceability

| Product decision | Source basis | Implementation evidence |
| --- | --- | --- |
| Enforce tenant scope in PostgreSQL as well as the host | PostgreSQL row security policies; NIST access-control principles | `0002_tenant_audit_boundary.sql`, cross-tenant integration tests |
| Bind tenant context to one transaction | PostgreSQL `set_config` and `current_setting` semantics | `PostgresPeopleRepository._transaction`, missing-context test |
| Preserve immutable audit evidence with the mutation | NIST audit and accountability control family | `audit_event`, same transaction write path, append-only trigger |
| Preserve effective and recorded time separately | Temporal database literature; ISO date/time representation | foundation schema and bitemporal domain kernel |
| Keep HR reporting semantics versioned | ISO 30414:2025 | job/criterion/decision versioning roadmap |

## APA 7 references

International Organization for Standardization. (2019). *ISO 8601-1:2019: Date
and time—Representations for information interchange—Part 1: Basic rules*.
https://www.iso.org/standard/70907.html

International Organization for Standardization. (2025). *ISO 30414:2025: Human
resource management—Requirements and recommendations for human capital
reporting and disclosure*. https://www.iso.org/standard/86602.html

Joint Task Force. (2020). *Security and privacy controls for information systems
and organizations* (NIST Special Publication 800-53, Revision 5). National
Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

PostgreSQL Global Development Group. (2026a). *PostgreSQL 18 documentation:
Row security policies*. https://www.postgresql.org/docs/18/ddl-rowsecurity.html

PostgreSQL Global Development Group. (2026b). *PostgreSQL 18 documentation:
System administration functions*. https://www.postgresql.org/docs/18/functions-admin.html

Snodgrass, R. T. (1999). *Developing time-oriented database applications in
SQL*. Morgan Kaufmann.

## Review notes

- PostgreSQL row-level security is defense in depth, not authentication.
- A custom PostgreSQL setting is not a credential; a generic SQL surface could
  set it and is therefore outside the allowed application boundary.
- `NOBYPASSRLS` and non-owner application roles are required in deployment.
- Encryption, key management, retention, backup, restoration, incident response
  and independent control testing remain separate release gates.
