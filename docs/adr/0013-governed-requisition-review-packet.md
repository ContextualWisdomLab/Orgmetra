# ADR 0013: Governed requisition review packet

- Status: Accepted on active implementation branch
- Date: 2026-08-18
- Owners: Talent Acquisition / Job Architecture / People Governance

## Context

Protected Orgmetra identifies requisitions as Talent Acquisition-owned records, but starting recruitment also depends on evidence owned by other HRIS domains: the authoritative Job, optionally one exact Position seat, current job requirements, and approved headcount. A buyer needs a reviewable handoff without creating a shadow candidate store, copying employee PII, conflating Job with Position, leaking human-readable/value-bearing trust metadata, or treating a generated packet as proof that a human approved the opening. Different opaque actor-reference strings also do not by themselves prove that the hiring manager and approver resolve to different authoritative actor identities.

Current ISO 30405:2023 frames recruitment as an organizational process that includes preparation and planning, stakeholder management, and review. U.S. OPM guidance describes job analysis as the foundation for assessment and selection decisions and emphasizes documented links among job tasks, competencies, and selection content. Shippmann et al. (2000) likewise examines the rigor and documented linkage expected when competency models are used in staffing contexts.

## Decision

Orgmetra will expose a transport-neutral `RequisitionReviewPacket` as non-authoritative review evidence before requisition approval. The packet binds:

- one canonical tenant;
- one UUID-backed opaque requisition reference;
- one UUID-backed authoritative Job reference;
- an optional separate UUID-backed Position reference;
- one UUID-backed versioned job-requirements reference and lowercase SHA-256 digest;
- one UUID-backed opaque headcount-authorization reference;
- UUID-backed accountable hiring-manager and approver actor references;
- bounded requested opening count, fixed purpose, reviewed non-sensitive reason metadata, numeric requirements-version metadata, and generation time.

All trust-bearing references require the expected namespace plus a canonical, non-sentinel UUID suffix. Human-readable or value-bearing suffixes are rejected before serialization. `requirements_version_code` is restricted to `requirements_version_<positive-integer>`, and the initial `reason_code` vocabulary is closed to `approved_growth_plan`. The generated dataclass representation is disabled and replaced with `RequisitionReviewPacket(<redacted>)`; canonical JSON is the explicit evidence serialization boundary.

The state is fixed to `requires_human_approval` with mandatory human confirmation. Identical hiring-manager and approver references are rejected as an early syntactic guard. Before approval, however, the host must re-resolve both actor references within the exact packet tenant through the authoritative actor boundary and reject approval unless their resolved actor identities are distinct. Reference inequality alone is not separation-of-duties evidence.

The packet cannot claim approval, open a requisition, create a candidate, or perform a selection decision. When a Position is supplied, it represents one exact seat and therefore authorizes exactly one opening; multi-opening requisitions remain Job-scoped until individual Position seats are allocated.

## Consequences

- Job and Position stay separate rather than being collapsed into a requisition label.
- Candidate and employee PII values are absent from the packet; opaque correlation references remain sensitive metadata rather than anonymous data.
- Job-requirements evidence is referential and versioned, allowing later Job Analysis implementations to satisfy the contract without this package owning their tables.
- Headcount authorization is an opaque reference rather than a copied finance or payroll record.
- Free-form semantic reference suffixes, personal/value-bearing reason text, and semantic requirements-version text cannot enter canonical evidence through direct construction or `dataclasses.replace(...)`.
- Routine `repr()` output does not disclose trust-bearing references or digests.
- Requisition approval requires authoritative resolved-actor separation; two different opaque references alone cannot satisfy the hiring-manager/approver separation requirement.
- Downstream persistence must still enforce purpose-bound authorization, idempotency, human approval, and immutable audit/outbox evidence at the authoritative mutation boundary.
- This ADR describes active-PR truth only until the corresponding exact head integrates into protected `develop`.

## References

See `docs/doctoring/requisition-review-references.md`.
