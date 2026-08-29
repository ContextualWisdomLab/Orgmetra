# ADR 0026: Normalize candidate applications away from candidate identity

- Status: Proposed
- Provenance: active PR; not protected-main truth until merged
- **Date:** 2026-08-21
- **Decision owner:** Orgmetra

## Context

Protected `develop` stores `application_status_code` directly on `candidate_profile`. That shape is not a defensible authoritative recruiting model once one candidate can pursue more than one opening: application lifecycle is contextual to an opening, while candidate identity persists across openings and reapplications. A single status on the candidate therefore conflates identity with an application-specific process state.

Orgmetra already keeps Job, Position, Assignment and candidate-to-worker conversion as separate concepts. The governed requisition-review contract also emits an opaque `requisition:<uuid>` reference and distinguishes the approved Job from an optional Position seat. The persistence model should preserve the same separation without reaching into another service's tables.

ISO 30405:2023 treats recruitment as a process with distinct phases and stakeholders. ISO 30201:2026 is the current published HR management-system requirements standard and includes attraction of workers inside the HR management system. HR Open Standards' approved Recruiting 4.2 material uses the distinct official objects `Candidate` and `PositionOpening`; the current Recruiting project also describes application-form and talent-pipeline exchanges. These sources support keeping candidate identity, opening context and application lifecycle separately addressable; they do not prescribe Orgmetra's physical schema.

## Decision

Migration `0014_candidate_application_core.sql` introduces three tenant-owned relations with separate identity and version responsibilities:

1. `candidate_application_record` is the immutable durable application anchor. It binds one candidate profile to one opaque requisition correlation and preserves submission/system-recorded creation time. One tenant/candidate/requisition tuple identifies one application anchor; corrections do not mint a replacement application ID.
2. `candidate_application_record_version` stores bitemporal opening scope for that stable application: the Job and optional Position, where a supplied Position must structurally belong to the same Job. Corrected opening-scope knowledge closes one recorded interval and appends a replacement version under the same `candidate_application_record_id`.
3. `candidate_application_stage_record` stores bitemporal operational pipeline stages for that same stable application. The closed vocabulary is intentionally limited to non-terminal process stages: `received`, `screening`, `assessment`, `interview`, and `offer_pending`.

Candidate-specific terminal values such as `hired`, `rejected`, ambiguous `closed`, or `withdrawn` are deliberately **not** raw application-stage values in this slice. Employer high-impact outcomes continue to require the existing `selection_decision` boundary with accountable human confirmation, purpose/reason/evidence versioning and sealed evidence. A withdrawal is only safe to treat as candidate-driven when the initiating actor and authoritative withdrawal evidence can be proven; this schema has no such provenance column or governed withdrawal event yet. Administrative opening closure belongs to the requisition/opening lifecycle rather than being encoded as a candidate-specific adverse stage.

The migration adds a tenant-qualified `(tenant_record_id, position_record_id, job_profile_id)` candidate key on `position_record`. An optional application Position version uses that exact composite key, so a seat from another Job cannot be attached by application code or stale caller state.

The durable application anchor is immutable rather than bitemporally replaced. Opening-scope versions and stage facts use system-recorded intervals; both also use effective business-time intervals and GiST exclusions so contradictory versions cannot be simultaneously true at the same effective and recorded coordinates. Corrections close an open recorded version and append replacement knowledge while preserving the same application anchor. In-place version/stage rewrites and deletion use the existing `protect_bitemporal_history()` boundary. All three relations force tenant row-level security and reject TRUNCATE where history exists.

The existing `candidate_profile.application_status_code` remains physically present for backward compatibility and is documented as legacy/unscoped. New canonical recruiting workflow state belongs to `candidate_application_stage_record`. Removing or backfilling the legacy column is a separate migration after callers have moved to the normalized contract.

## Privacy and authority boundary

The new relations contain no candidate name, email, demographic field, assessment value, résumé content or model output. Candidate identity is referenced by opaque UUID; requisition correlation uses the existing opaque `requisition:<uuid>` namespace. Tenant-qualified foreign keys and forced RLS enforce structural tenant isolation.

`requisition_reference` is correlation to Orgmetra's governed requisition evidence contract, not proof that an opening was approved. Hosts must still resolve the authoritative requisition-review evidence before opening or mutating a recruiting workflow. This migration does not create direct SQL coupling to any other CWL service.

## Consequences

- A single candidate can be represented correctly across simultaneous or repeated openings without overwriting one global application status.
- One application keeps one durable identifier while Job/Position scope corrections append bitemporal version knowledge, so stage history cannot become stranded on a retired application ID.
- Position-specific recruiting cannot silently target a seat whose durable Job differs from the application Job.
- Historical opening scope and stage reconstruction are bitemporal and correction-safe; adjacent corrections are allowed while overlapping effective/system truth is rejected.
- Final selection outcomes remain centralized in the existing high-impact decision model instead of being smuggled into workflow codes.
- Candidate withdrawal cannot be represented as a bare status until a governed boundary proves candidate initiation and immutable evidence; this fails closed rather than permitting staff to use `withdrawn` as a shadow rejection.
- Existing readers of `candidate_profile.application_status_code` continue to work during migration, but that field is legacy and cannot represent the normalized source of truth.
- A later bounded slice may bind `selection_decision` directly to `candidate_application_record`, add a governed candidate-withdrawal event, and provide application command/API surfaces; this ADR does not claim those are implemented.

## Rejected alternatives

### Keep one status on `candidate_profile`

Rejected because candidate identity and application lifecycle have different cardinalities and lifetimes. It cannot represent two concurrent applications without overwriting state.

### Close and recreate `candidate_application_record` to correct opening scope

Rejected because `candidate_application_record_id` is the durable application identity referenced by stage history and later candidate/decision evidence. Replacing that ID during a correction strands dependent history on the retired anchor. Mutable Job/Position scope therefore belongs in `candidate_application_record_version`.

### Store application state only in requisition-review packets

Rejected because a review packet is immutable approval/correlation evidence, not the operational HRIS application lifecycle. Treating the packet as mutable process state would blur governance evidence and authoritative HR data.

### Encode terminal outcomes as ordinary workflow stages

Rejected because `hired`, `rejected`, or ambiguous `closed` can imply high-impact employer outcomes, while a bare `withdrawn` value does not prove candidate initiation. Orgmetra must not create a weaker shadow decision path or unaudited terminal-state shortcut. Administrative requisition closure belongs to the requisition/opening lifecycle; candidate withdrawal requires a separate governed evidence boundary.

## Evidence

- `tests/test_candidate_application_postgres.sh` is the primary PostgreSQL contract. It owns schema/fixture creation and proves multiple application anchors per candidate, cross-tenant FK rejection, Position↔Job consistency, duplicate candidate/requisition rejection, stable-anchor immutability, bitemporal opening-scope correction under the same anchor, overlapping scope-history rejection, bitemporal stage exclusion/correction, prohibition on a `hired` workflow stage, forced-RLS metadata and TRUNCATE protection.
- `tests/test_candidate_application_decision_boundary_postgres.sh` runs **after** the primary contract against the same service/fixtures. It proves the stable version relation exists, application ID remains stable, stage history stays attached to a live anchor, and raw workflow rejects both ambiguous `closed` and unproven `withdrawn` terminal states. It is not an independently runnable schema-setup contract.
- `tests/test_candidate_application_rls_postgres.sh` also runs **after** the primary contract and reuses those fixtures. Under a `NOBYPASSRLS` role it proves fail-closed missing-context reads, tenant-local visibility across anchor/version/stage relations, cross-tenant invisibility, and rejection of a cross-tenant INSERT through the policy `WITH CHECK` path. It is not an independently runnable schema-setup contract.
- `.github/workflows/candidate-application-quality.yml` checks out the exact PR head and executes those contracts in the required order against pinned PostgreSQL 16.14.
- Primary-source review and APA 7 references are recorded in `docs/doctoring/candidate-application-references.md`.
