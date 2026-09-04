# Employment absence truth traceability

## Status

- **Protected-main truth:** `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` has bitemporal Employment and Assignment facts but no reason-free authoritative Employment absence fact or snapshot builder.
- **Active PR truth:** PR #113 (`feat/employment-absence-truth`) adds `EmploymentAbsenceVersion`, `EmploymentAbsenceSnapshot`, and `build_employment_absence_snapshot(...)` in the HRIS kernel.
- **Not yet accepted architecture:** durable PostgreSQL persistence, People API mutation/read surfaces, entitlement/case management, scheduling/payroll effects, and UI remain separate future boundaries.
- **Out of scope:** medical, family, statutory, disciplinary, free-form, benefit, compensation, credential, or model-output content.

## Requirement-to-evidence map

| Requirement | Owner | Executable evidence |
|---|---|---|
| Reconstruct absence at one business date and system-knowledge cutoff | HRIS kernel | `packages/hris-kernel/tests/test_employment_absence.py` |
| Keep tenant, Employment, and Person bindings fail-closed | HRIS kernel | person mismatch, foreign-tenant, missing/terminal Employment regressions |
| Reject UUID/date/status runtime subclass forgery before tenant/identity comparison or canonical export | HRIS kernel | `test_employment_absence_runtime_integrity.py` |
| Support correction-not-rewrite | HRIS kernel | recorded-time confirmed→cancelled regression |
| Reject contradictory visible versions | shared bitemporal resolver | duplicate Employment/absence version regressions |
| Reject overlapping operational absence identities | HRIS kernel | multiple-confirmed-absence regression |
| Normalize failing/stateful caller timezone behavior before bitemporal comparison/export | HRIS kernel | `test_employment_absence_timezone_integrity.py` |
| Do not expose sensitive leave reason or Person identifier in canonical snapshot evidence | HRIS kernel | canonical evidence minimization regression |
| Produce deterministic audit-correlation bytes | HRIS kernel | `canonical_document()`, `canonical_json()`, `content_digest()` regression |
| Preserve high-impact human authority outside descriptive absence truth | downstream authorized host | no mutation/decision method exists in this slice |

## Data contract

`EmploymentAbsenceVersion` is a bitemporal version of one durable `employment_absence_record_id`. It binds one tenant, Employment, and Person to an effective interval and recorded interval. `absence_status_code` is deliberately limited to exact built-in-string `confirmed` or `cancelled`; it does not encode why the worker is absent.

At a requested coordinate, `build_employment_absence_snapshot(...)` requires exact built-in UUID scope identities and an exact built-in business `date` before any tenant/identity or interval comparison. The relevant UUID fields carried by candidate Employment and absence facts are also validated before scope filtering, preventing caller-defined UUID equality/hash/display behavior from fabricating cross-tenant or cross-Employment visibility. Exactly one visible same-tenant Employment version in status `active` or `leave` is required. Every visible durable absence identity must resolve to at most one version, and at most one `confirmed` operational absence may be visible for the Employment. A cancelled version is retained as historical truth but does not mark the Employment absent.

The caller-supplied knowledge cutoff must be an exact built-in `datetime` with a concrete UTC offset. Orgmetra evaluates that timezone provider once, converts the coordinate to a built-in UTC datetime, and uses only the frozen UTC value for subsequent bitemporal comparison and canonical evidence. Provider-specific exceptions are normalized to `EmploymentAbsenceError` rather than escaping the public boundary. This prevents stateful or failing caller timezone code from changing checked-versus-emitted system-time evidence or error semantics.

Direct `EmploymentAbsenceSnapshot` construction enforces the same exact UUID/date/datetime primitives and an exact built-in boolean `is_absent`; an absence identifier is present if and only if the snapshot is absent. Canonical snapshot evidence therefore contains only opaque tenant/Employment/absence identifiers, trusted effective and knowledge coordinates, a real JSON boolean absence state, and schema version. Person identity and leave reason are intentionally excluded.

## Safety and privacy boundary

This slice answers **whether** an Employment is absent at one bitemporal coordinate. It does not answer why, determine legal entitlement, decide discipline, change Assignment or Position state, calculate benefits/pay, or authorize any employment action. Sensitive leave-case details belong behind a purpose-bound case/authorization boundary and must not be copied into this core operational fact.

The design follows data-minimization and purpose-limitation principles as architectural risk controls; it does not claim GDPR, FMLA, NIST, SOC 2, or any other certification or jurisdictional compliance. See `docs/doctoring/employment-absence-truth-references.md`.

## Merge/release boundary

Active-PR evidence remains non-authoritative until the unchanged exact head has terminal GREEN applicable tests/security/recovery evidence, qualifying independent non-author review where required, and actual enforceable repository protection. Issue #89 owns the repository-settings defect; this PR must not simulate protection in workflow or application code.
