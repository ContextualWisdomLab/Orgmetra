# ADR 0113: Keep operational Employment absence truth reason-free and bitemporal

## Status

Accepted on active implementation branch (PR #113). This is not protected-main truth until merged.

## Context

Orgmetra can reconstruct Employment and Assignment history, and a separate active PR provides human-review-only leave-request evidence, but protected `develop` cannot answer the operational question: "Was this Employment absent on this business date, using only what the system knew at this recorded-time cutoff?"

Copying leave reasons into the HRIS kernel would enlarge the privacy and authorization blast radius. Family, medical, statutory, disciplinary, benefits, and other case details can be both jurisdiction-specific and sensitive while the scheduling/workforce core usually needs only the operational absence fact.

## Decision

Add a durable `EmploymentAbsenceVersion` bitemporal fact keyed by tenant, Employment, Person, durable absence identity, effective time, and recorded time. Its operational state is limited to `confirmed` or `cancelled`; it carries no reason/category payload.

Add `build_employment_absence_snapshot(...)` to reconstruct one coordinate. The builder:

1. requires a timezone-aware knowledge cutoff;
2. rejects Person rebinding inside a tenant;
3. requires exactly one visible same-tenant Employment anchor in `active` or `leave` status;
4. resolves at most one version per durable absence identity;
5. rejects more than one confirmed operational absence for the same Employment coordinate; and
6. emits deterministic PII-minimized canonical evidence without the Person identifier or absence reason.

The core fact is descriptive truth only. It does not decide leave entitlement, discipline, compensation, benefits, scheduling, return-to-work, or any other high-impact employment action.

## Consequences

- Operational consumers can reconstruct absence without copying sensitive leave-case details into a second HR store.
- Corrections preserve both effective/business time and system-recorded time rather than rewriting history.
- Multiple legal/medical case records that overlap must be resolved behind the purpose-bound case boundary into one operational absence truth; the kernel fails closed instead of double-counting them.
- Durable database persistence, purpose-bound People API access, audit/outbox application, and UI remain later owner boundaries and must preserve this reason-free contract.
- The design intentionally does not encode jurisdiction-specific FMLA/GDPR eligibility or claim NIST/SOC 2 certification.

## References

See `docs/doctoring/employment-absence-truth-references.md` for primary-source references and final-vs-draft standard status.
