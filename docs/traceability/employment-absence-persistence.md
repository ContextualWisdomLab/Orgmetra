# Employment absence persistence traceability

This document distinguishes protected-default-branch truth from the active stacked PR. It is not merge-control evidence.

| Requirement | Owner boundary | Executable evidence |
|---|---|---|
| Stable absence identity is separate from temporal versions | HRIS core | `employment_absence_record` / `employment_absence_version` schema regression |
| Same-tenant Employment and Person binding | HRIS core | composite FK plus PostgreSQL contract |
| Business-effective and system-recorded time remain separate | HRIS core | effective/recorded columns and bitemporal exclusion constraint |
| System-recorded creation/version time is database-owned | HRIS core | caller-backdating regression |
| Corrections close history instead of rewriting it | HRIS core | permitted current-time `recorded_to` closure plus immutable-field regression |
| Persisted absence interval has active/leave Employment coverage | HRIS core | full-range coverage negative regression |
| At most one overlapping confirmed absence fact per Employment | HRIS core | serialized second-anchor rejection regression |
| Tenant visibility is fail-closed | HRIS core | ENABLE + FORCE RLS and `NOBYPASSRLS` reader regression |
| Sensitive leave reasons are absent from generic core storage | HRIS core | forbidden-column regression |
| Operational absence does not authorize high-impact decisions | HRIS core | fixed `not_authorized_for_employment_decision` state |
| Audit/outbox integration does not use cross-service application-table SQL | published owner contracts | opaque references and evidence digests only |
| Exact candidate is reproducible in CI | repository CI | exact-head checkout, deterministic file hashes, clean-checkout gate |

## State boundaries

- **Protected/default branch:** `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` does not contain Employment absence persistence.
- **Parent active PR:** #113 supplies reason-free in-memory bitemporal absence truth at exact parent head `3da7ad076f977a3ccd9e130a58786c9d26763a16`.
- **This active PR:** introduces migration `0026`, its PostgreSQL contract, dedicated workflow, ADR 0114, and this traceability record.
- **Planned after parent integration:** retarget to fresh `develop`, reconcile migration sequence, and rerun Foundation/SAST/Security/Recovery/People/Workforce/Job-Analysis plus the focused persistence gate.
- **Out of scope:** medical/family/statutory/disciplinary leave-case data, benefits adjudication, payroll calculations, attendance discipline, and automated employment decisions.
