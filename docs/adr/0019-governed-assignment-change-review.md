# ADR 0019: Governed assignment-change review before authoritative mutation

- **Status:** Proposed — active PR truth only
- **Date:** 2026-08-19

## Context

Protected Orgmetra separates Job, Position, Assignment, Employment, and Person truth and applies bitemporal and purpose-bound governance. It does not yet expose a bounded review artifact for an internal reassignment or work-allocation change that can be inspected by an accountable human before an authoritative mutation occurs.

A high-value assignment change can affect the worker, organizational capacity, operations, and downstream reporting. Merely carrying valid record identifiers does not prove that the current Employment/Assignment/Job/Position relationships are authoritative at the intended effective date or that the proposed Position belongs to the intended Job and has capacity. Different opaque requester/reviewer references likewise do not prove distinct authoritative actor identities. Copying worker, compensation, allocation, or sensitive personal-reason values into an orchestration envelope would also expand the privacy boundary unnecessarily. Protected Orgmetra core already owns tenant identity semantics and accepts canonical non-sentinel operational UUIDs, including UUIDv7; this leaf package must not replace that contract with a UUIDv4-only tenant rule. UUIDv4 remains the packet-owned privacy rule for namespaced trust references.

Python `frozen=True` is not an adversarial issuance boundary: low-level allocation can create a packet-shaped object without a normal full constructor, and `object.__setattr__` can rewrite otherwise valid fields. A process-local HMAC alone is therefore insufficient if an allocator-bypassed object can later copy valid fields, call `__post_init__()`, and register its own fresh seal. Constructor provenance must be tied to the exact live object that entered through the normal full class call, and that privilege must be consumed before caller-owned timezone code executes so a reentrant `tzinfo.utcoffset()` callback cannot retain a second allocator-created object with ambient issuance privilege.

ISO 30434:2023 describes workforce allocation as a managed process involving allocation decisions and stakeholders, including workers, and calls for allocation processes to be documented, communicated, measured, and improved. ISO 30435:2023 focuses on determination, capture, maintenance, and review of quality workforce data. ISO 30201:2026 establishes requirements for an HR management system integrated with organizational management and risk management. The U.S. OPM Guide to Processing Personnel Actions is a jurisdiction-specific operational example in which personnel actions are documented and position-change actions are subject to approval/effective-date controls. These sources inform the evidence boundary; they are not incorporated as certification claims or universal legal rules.

## Decision

Add a transport-neutral `AssignmentChangeReviewPacket` that:

1. correlates one authoritative Orgmetra tenant, Person, Employment, current Assignment/Job/Position, proposed Job/Position, current-scope snapshot, workforce-allocation plan, exact allocation-policy version, worker-impact assessment, communication plan, requester, reviewer, controlled reason category, requested effective date, evidence version, and evidence-generation instant;
2. requires `tenant_record_id` to satisfy the protected-core canonical non-sentinel operational-UUID contract while packet-owned trust-bearing HR and evidence identities remain expected-namespace canonical non-sentinel UUIDv4 references, with lowercase SHA-256 digests for evidence artifacts;
3. keeps Person PII, compensation values, numeric allocation values, free-form model output, and free-form personal reasons outside the envelope;
4. limits `reason_code` to reviewed operational categories (`internal_reassignment`, `workforce_reallocation`, `temporary_detail`, `position_reclassification`, `organizational_realignment`) so the governance envelope cannot become an accidental sensitive narrative channel;
5. includes a bounded positive `evidence_version` in canonical JSON/SHA-256 so actor/purpose/reason evidence from different review-contract revisions cannot silently collide;
6. rejects identical requester/reviewer references as an early syntactic guard and requires tenant-scoped authoritative actor resolution proving the resolved identities are distinct before approval;
7. records `scope_verification_state=requires_authoritative_resolution` because reference correlation alone cannot prove bitemporal relationship validity;
8. records `mutation_state=not_authorized_to_apply`; creation or hashing of the packet is never approval or mutation evidence;
9. directs the host, immediately before approval, to re-resolve **every packet reference within `tenant_record_id`**, prove requester/reviewer resolved-actor separation, verify the Person-to-Employment-to-current-Assignment binding and current Assignment/Job/Position worker scope, and then verify proposed Job/Position binding/capacity, exact policy, worker-impact, communication, and effective-date requirements before invoking the authoritative People mutation boundary; and
10. makes construction provenance one-shot and exact-object bound: a private metaclass arms a context-local allocator ticket for a normal `AssignmentChangeReviewPacket(...)` call, the exact packet `__new__()` consumes it immediately before validation or caller-controlled timezone callbacks, and `__post_init__()` requires that exact live-object provenance before registering issuance;
11. binds successful governed construction to exact canonical JSON with a process-local HMAC seal stored outside packet-writable slots, records the exact live identity as issued, refuses a second issuance registration for that identity, and requires exact issued-identity membership plus the matching seal before canonical export.

Direct `object.__new__` allocation, direct packet-allocator calls, allocator calls reached reentrantly from `tzinfo.utcoffset()`, copied fields, and manual `__post_init__()` therefore cannot create new issuance evidence outside the normal construction path. The package performs no database write, no direct cross-service application-table SQL, no actor-identity resolution, and no provider execution. Purpose-bound authorization, transactional idempotency, immutable audit/outbox, bitemporal persistence, durable cross-process attestation, and hostile-interpreter isolation remain separate authoritative controls.

## Consequences

Buyers gain a deterministic, explicitly versioned, PII-minimized review handoff that can be audited without treating the packet as an employment action. Internal mobility and allocation workflows can use one contract while preserving Job/Position/Assignment separation and keeping the eventual mutation under protected HRIS ownership. Separation of duties is proven by authoritative actor resolution rather than by opaque-reference inequality. Authoritative UUIDv7 tenant identities remain interoperable, while UUIDv1 timestamp/node correlation remains excluded from packet-owned namespaced trust references.

The trade-off is deliberate: consumers must resolve every bound reference in the exact tenant context, prove distinct requester/reviewer actor identities, and verify the Person/Employment/current-Assignment worker binding plus proposed scope and applicable policy at decision time. A valid packet cannot prove Position capacity, effective-date legality, worker consultation, collective-agreement compliance, or successful persistence on its own. The context-local constructor ticket, weak live-identity registries, and process-local issuance seal are defense-in-depth against allocator bypass, in-process evidence mutation, and seal renewal; they are not a hostile-interpreter capability boundary, portable signature, rehydration credential, durable authorization, or immutable persistence mechanism.

## References

See `docs/doctoring/assignment-change-review-references.md`.
