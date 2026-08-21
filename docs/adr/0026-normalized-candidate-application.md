# ADR 0026: Normalize candidate applications away from candidate identity

- **Status:** Proposed on active PR; not protected-main truth until merged
- **Date:** 2026-08-21
- **Decision owner:** Orgmetra

## Context

Protected `develop` stores `application_status_code` directly on `candidate_profile`. That shape is not a defensible authoritative recruiting model once one candidate can pursue more than one opening: application lifecycle is contextual to an opening, while candidate identity persists across openings and reapplications. A single status on the candidate therefore conflates identity with an application-specific process state.

Orgmetra already keeps Job, Position, Assignment and candidate-to-worker conversion as separate concepts. The governed requisition-review contract also emits an opaque `requisition:<uuid>` reference and distinguishes the approved Job from an optional Position seat. The persistence model should preserve the same separation without reaching into another service's tables.

ISO 30405:2023 treats recruitment as a process with distinct phases and stakeholders. ISO 30201:2026 is the current published HR management-system requirements standard and includes attraction of workers inside the HR management system. HR Open Standards' approved Recruiting 4.2 material distinguishes Candidate Record from Position Opening, while its current Recruiting workgroup explicitly continues work on application-form and talent-pipeline schemas. These sources support keeping candidate identity, opening context and application lifecycle separately addressable; they do not prescribe Orgmetra's physical schema.

## Decision

Migration `0014_candidate_application_core.sql` introduces two tenant-owned relations:

1. `candidate_application_record` is a durable application identity. It binds one candidate profile to one Job, an optional Position that must structurally belong to that same Job, and one opaque requisition reference. A candidate may have multiple application identities, but only one application for the same requisition reference within a tenant.
2. `candidate_application_stage_record` stores bitemporal operational pipeline stages for one application. The closed vocabulary is intentionally limited to non-outcome workflow stages: `received`, `screening`, `assessment`, `interview`, `offer_pending`, `withdrawn`, and `closed`.

`hired` and `rejected` are deliberately **not** application-stage values. Employer high-impact outcomes continue to require the existing `selection_decision` boundary with accountable human confirmation, purpose/reason/evidence versioning and sealed evidence. An operational stage must not become a shadow employment decision.

The migration adds a tenant-qualified `(tenant_record_id, position_record_id, job_profile_id)` candidate key on `position_record`. An optional application Position uses that exact composite key, so a seat from another Job cannot be attached by application code or stale caller state.

Application and stage histories use system-recorded intervals. Stage facts additionally use effective business-time intervals and a GiST exclusion constraint so contradictory stages cannot be simultaneously true at the same effective and recorded coordinates. Corrections close an open recorded interval and append replacement knowledge; in-place rewrites and deletion use the existing `protect_bitemporal_history()` boundary. Both new relations force tenant row-level security and reject TRUNCATE.

The existing `candidate_profile.application_status_code` remains physically present for backward compatibility and is documented as legacy/unscoped. New canonical recruiting workflow state belongs to `candidate_application_stage_record`. Removing or backfilling the legacy column is a separate migration after callers have moved to the normalized contract.

## Privacy and authority boundary

The new relations contain no candidate name, email, demographic field, assessment value, résumé content or model output. Candidate identity is referenced by opaque UUID; requisition correlation uses the existing opaque `requisition:<uuid>` namespace. Tenant-qualified foreign keys and forced RLS enforce structural tenant isolation.

`requisition_reference` is correlation to Orgmetra's governed requisition evidence contract, not proof that an opening was approved. Hosts must still resolve the authoritative requisition-review evidence before opening or mutating a recruiting workflow. This migration does not create direct SQL coupling to any other CWL service.

## Consequences

- A single candidate can be represented correctly across simultaneous or repeated openings without overwriting one global application status.
- Position-specific recruiting cannot silently target a seat whose durable Job differs from the application Job.
- Historical stage reconstruction becomes bitemporal and correction-safe.
- Final selection outcomes remain centralized in the existing high-impact decision model instead of being smuggled into workflow codes.
- Existing readers of `candidate_profile.application_status_code` continue to work during migration, but that field is legacy and cannot represent the normalized source of truth.
- A later bounded slice may bind `selection_decision` directly to `candidate_application_record` and provide governed application command/API surfaces; this ADR does not claim those are implemented.

## Rejected alternatives

### Keep one status on `candidate_profile`

Rejected because candidate identity and application lifecycle have different cardinalities and lifetimes. It cannot represent two concurrent applications without overwriting state.

### Store application state only in requisition-review packets

Rejected because a review packet is immutable approval/correlation evidence, not the operational HRIS application lifecycle. Treating the packet as mutable process state would blur governance evidence and authoritative HR data.

### Encode `hired` or `rejected` as ordinary workflow stages

Rejected because those values can imply high-impact employment outcomes. Orgmetra already has a stricter `selection_decision` evidence boundary and must not create a second, weaker decision path.

## Evidence

- `tests/test_candidate_application_postgres.sh` is the RED-first PostgreSQL regression. It proves multiple applications per candidate, cross-tenant FK rejection, Position↔Job consistency, duplicate requisition rejection, bitemporal stage exclusion/correction, prohibition on a `hired` workflow stage, forced RLS and TRUNCATE protection.
- `.github/workflows/candidate-application-quality.yml` checks out the exact PR head and runs that contract against pinned PostgreSQL 16.14.
- Primary-source review and APA 7 references are recorded in `docs/doctoring/candidate-application-references.md`.
