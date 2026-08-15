# Purpose-bound PostgreSQL traceability

| Requirement | Design decision | Source | Test or evidence | Maturity |
| --- | --- | --- | --- | --- |
| Authorized HR PII remains usable | Purpose-bound access rather than blanket masking | `PurposeContext`, ADR-0005 | context validation and RLS integration tests | implemented_on_active_pr |
| Tenant A cannot read tenant B | Forced database row-level security | migration `0002` | `test_tenant_person_audit_and_rls_round_trip` | implemented_on_active_pr |
| Missing context fails closed | RLS policy compares every row with transaction-local tenant | migration `0002` | no-context app-role query returns zero | implemented_on_active_pr |
| Cross-tenant relationships fail | Composite tenant foreign keys | migration `0002` | relationship-integrity test | implemented_on_active_pr |
| Business mutation and audit do not diverge | Same PostgreSQL transaction | repository `_record_audit` | integration and conflict rollback paths | implemented_on_active_pr |
| High-impact facts are append-only | Database triggers | ADR-0005 and migration `0002` | immutable audit update rejection | implemented_on_active_pr |
| Errors do not expose SQL or PII | Stable repository exception taxonomy | repository errors | unit failure-translation tests | implemented_on_active_pr |
| Database names are descriptive snake_case | Static naming contract | SQL migration | `test_created_database_objects_use_descriptive_snake_case` | implemented_on_active_pr |
| Production code is fully explained and exercised | Public docstrings and exact coverage gate | CI workflow | coverage JSON and docstring audit | implemented_on_active_pr |
| Existing populated tenants can upgrade safely | Expand/backfill/validate/contract migration | ADR-0005 | not yet implemented | planned |
| Images and dependencies are immutable and attested | Release supply-chain contract | operability backlog | not yet implemented | planned |
| Backup, restore and PITR are demonstrated | Recovery contract | operability backlog | not yet implemented | planned |

`implemented_on_active_pr` is not shipped behavior. The table must be revised to
`implemented_on_protected_main` only after the dependency stack, exact-head
checks, independent review and protected merge have completed.
