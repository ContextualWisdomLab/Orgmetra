# Enterprise Architecture projection admission

This package is the Orgmetra-side admission boundary for Enterprise Architecture projection candidates. It exists to keep two systems of record separate: Orgmetra owns HRIS/HCM facts, while the Enterprise Architecture Decision Plane owns accepted architecture truth.

It does **not** publish directly to Enterprise Architecture Core, reproduce `context-graph-contracts`, or carry person, employment, job, position, assignment, performance, selection, or other authoritative HR record payloads. Cross-service database access is not part of this boundary.

## Current operating state

A candidate is blocked until a trusted control-plane lookup has observed an immutable published `ContextualWisdomLab/context-graph-contracts` release and supplied its stable release tag, exact commit SHA, artifact SHA-256, publication state, and timezone-aware verification time. Shape validation in this package is not proof that the external release exists and must not be populated from untrusted request data.

Release identity alone is deliberately insufficient. The exact released commit and artifact must also be bound to trusted evidence for executable semantic conformance, the complete published contract bundle, and artifact provenance. Until those admission and provenance receipts are independently verified, `evaluate_projection_readiness` remains fail-closed with the next action `verify_released_context_graph_contract_admission`.

The package does not guess or reproduce an unreleased Context Assertion, CloudEvent, API schema, profile, admission receipt, or provenance format. The trusted control plane must obtain those semantics from the immutable released `context-graph-contracts` package and retain their exact evidence identities. When `context-graph-contracts` has no immutable release, the earlier gate remains `install_approved_context_graph_contract_release`.

Only after release identity and the release-bound conformance, complete-bundle, and provenance evidence are all admitted can Orgmetra produce a `proposed` candidate whose next action is `submit_candidate_to_enterprise_architecture_owner`. Acceptance, replacement, lifecycle decisions, and authoritative EA truth remain with the Enterprise Architecture owner.

## Candidate scope

Permitted projection concepts are deployable architecture concerns such as applications, interfaces, technology components and versions, providers, lifecycle, supported capabilities, initiatives, transformations, and dependencies. Projection evidence preserves Orgmetra source revision, effective time, recorded time, non-person ownership references, architecture-only dependency references, and the exact contract-admission evidence identities used for the handoff.

The package intentionally exposes no free-form payload field. If a future use case needs additional fields, add them explicitly with RED tests proving that HR record data cannot cross the boundary.
