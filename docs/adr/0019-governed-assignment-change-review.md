# ADR 0019: Governed assignment-change review before authoritative mutation

- **Status:** Proposed — active PR truth only
- **Date:** 2026-08-19

## Context

Protected Orgmetra separates Job, Position, Assignment, Employment, and Person truth and applies bitemporal and purpose-bound governance. It does not yet expose a bounded review artifact for an internal reassignment or work-allocation change that can be inspected by an accountable human before an authoritative mutation occurs.

A high-value assignment change can affect the worker, organizational capacity, operations, and downstream reporting. Merely carrying valid record identifiers does not prove that the current Employment/Assignment/Job/Position relationships are authoritative at the intended effective date or that the proposed Position belongs to the intended Job and has capacity. Copying worker or compensation values into an orchestration envelope would also expand the privacy boundary unnecessarily.

ISO 30434:2023 describes workforce allocation as a managed process involving allocation decisions and stakeholders, including workers, and calls for allocation processes to be documented, communicated, measured, and improved. ISO 30435:2023 focuses on determination, capture, maintenance, and review of quality workforce data. ISO 30201:2026 establishes requirements for an HR management system integrated with organizational management and risk management. The U.S. OPM Guide to Processing Personnel Actions is a jurisdiction-specific operational example in which personnel actions are documented and position-change actions are subject to approval/effective-date controls. These sources inform the evidence boundary; they are not incorporated as certification claims or universal legal rules.

## Decision

Add a transport-neutral `AssignmentChangeReviewPacket` that:

1. correlates one tenant, Person, Employment, current Assignment/Job/Position, proposed Job/Position, current-scope snapshot, workforce-allocation plan, worker-impact assessment, communication plan, requester, reviewer, reason, requested effective date, and evidence-generation instant;
2. represents trust-bearing HR and evidence identities only as expected-namespace canonical non-sentinel UUID references, with lowercase SHA-256 digests for evidence artifacts;
3. keeps Person PII, compensation values, numeric allocation values, and free-form model output outside the envelope;
4. requires requester/reviewer separation and exact human-review-only state;
5. records `scope_verification_state=requires_authoritative_resolution` because reference correlation alone cannot prove bitemporal relationship validity;
6. records `mutation_state=not_authorized_to_apply`; creation or hashing of the packet is never approval or mutation evidence; and
7. directs the host to re-resolve authoritative current/proposed scope, policy, capacity, worker-impact, communication, and effective-date requirements before recording accountable approval and invoking the authoritative People mutation boundary.

The package performs no database write, no direct cross-service application-table SQL, and no provider execution. Purpose-bound authorization, transactional idempotency, immutable audit/outbox, and bitemporal persistence remain separate authoritative controls.

## Consequences

Buyers gain a deterministic, PII-minimized review handoff that can be audited without treating the packet as an employment action. Internal mobility and allocation workflows can use one contract while preserving Job/Position/Assignment separation and keeping the eventual mutation under protected HRIS ownership.

The trade-off is deliberate: consumers must resolve the exact relationships and applicable policy at decision time. A valid packet cannot prove Position capacity, effective-date legality, worker consultation, collective-agreement compliance, or successful persistence on its own.

## References

See `docs/doctoring/assignment-change-review-references.md`.
