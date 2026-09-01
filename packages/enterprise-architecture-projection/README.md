# Enterprise Architecture projection admission

This package is the Orgmetra-side admission boundary for Enterprise Architecture projection candidates. It exists to keep two systems of record separate: Orgmetra owns HRIS/HCM facts, while the Enterprise Architecture Decision Plane owns accepted architecture truth.

It does **not** publish directly to Enterprise Architecture Core, reproduce `context-graph-contracts`, or carry person, employment, job, position, assignment, performance, selection, or other authoritative HR record payloads. Cross-service database access is not part of this boundary.

## Current operating state

A candidate is blocked until a trusted control-plane lookup has observed an immutable published `ContextualWisdomLab/context-graph-contracts` release and supplied its stable release tag, exact commit SHA, artifact SHA-256, publication state, and timezone-aware observation time. Shape validation in this package is not a substitute for that trusted lookup and must not be populated from untrusted request data.

When no approved contract release is available, `evaluate_projection_readiness` returns a fail-closed decision whose next action is `install_approved_context_graph_contract_release`.

When admissible release evidence is present, the result is still only a `proposed` candidate. Its next action is `submit_candidate_to_enterprise_architecture_owner`. Acceptance, replacement, lifecycle decisions, and authoritative EA truth remain with the Enterprise Architecture owner.

## Candidate scope

Permitted projection concepts are deployable architecture concerns such as applications, interfaces, technology components and versions, providers, lifecycle, supported capabilities, initiatives, transformations, and dependencies. Projection evidence preserves Orgmetra source revision, effective time, recorded time, non-person ownership references, and architecture-only dependency references.

The package intentionally exposes no free-form payload field. If a future use case needs additional fields, add them explicitly with RED tests proving that HR record data cannot cross the boundary.
