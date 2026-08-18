# ADR 0013: Governed requisition review packet

- Status: Accepted on active implementation branch
- Date: 2026-08-18
- Owners: Talent Acquisition / Job Architecture / People Governance

## Context

Protected Orgmetra identifies requisitions as Talent Acquisition-owned records, but starting recruitment also depends on evidence owned by other HRIS domains: the authoritative Job, optionally one exact Position seat, current job requirements, and approved headcount. A buyer needs a reviewable handoff without creating a shadow candidate store, copying employee PII, conflating Job with Position, or treating a generated packet as proof that a human approved the opening.

Current ISO 30405:2023 frames recruitment as an organizational process that includes preparation and planning, stakeholder management, and review. U.S. OPM guidance describes job analysis as the foundation for assessment and selection decisions and emphasizes documented links among job tasks, competencies, and selection content. Shippmann et al. (2000) likewise examines the rigor and documented linkage expected when competency models are used in staffing contexts.

## Decision

Orgmetra will expose a transport-neutral `RequisitionReviewPacket` as non-authoritative review evidence before requisition approval. The packet binds:

- one canonical tenant;
- one opaque requisition reference;
- one authoritative Job reference;
- an optional separate Position reference;
- one versioned job-requirements reference and lowercase SHA-256 digest;
- one opaque headcount-authorization reference;
- accountable hiring-manager and approver actor references;
- bounded requested opening count, purpose, reason, and generation time.

The state is fixed to `requires_human_approval` with mandatory human confirmation. The packet cannot claim approval, open a requisition, create a candidate, or perform a selection decision. When a Position is supplied, it represents one exact seat and therefore authorizes exactly one opening; multi-opening requisitions remain Job-scoped until individual Position seats are allocated.

## Consequences

- Job and Position stay separate rather than being collapsed into a requisition label.
- Candidate and employee PII are absent from the packet.
- Job-requirements evidence is referential and versioned, allowing later Job Analysis implementations to satisfy the contract without this package owning their tables.
- Headcount authorization is an opaque reference rather than a copied finance or payroll record.
- Downstream persistence must still enforce purpose-bound authorization, idempotency, human approval, and immutable audit/outbox evidence at the authoritative mutation boundary.
- This ADR describes active-PR truth only until the corresponding exact head integrates into protected `develop`.

## References

See `docs/doctoring/requisition-review-references.md`.
