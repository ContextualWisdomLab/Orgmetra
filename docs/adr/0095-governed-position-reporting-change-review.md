# ADR 0095: Governed Position reporting-change review before authoritative mutation

- **Status:** Proposed — active PR truth only
- **Date:** 2026-08-23

## Context

Orgmetra already separates Job, Position and Assignment and models effective/business time separately from system-recorded time. Buyers also need defensible organizational reporting-line change controls: a manager-position reassignment can alter authority, span of control, approvals and workforce reporting even when no Person record is changed.

Protected `develop` does not yet ship an authoritative Position-reporting mutation boundary. Active PR #94 adds a read-only bitemporal Position-to-Position hierarchy, but active-PR behavior cannot be treated as protected-main truth or imported as an undeclared branch dependency. A review artifact can still be valuable now if it remains transport-neutral, fail-closed and explicitly unable to mutate HRIS data.

NIST SP 800-53 Rev. 5 Release 5.2.0 retains AC-5 separation-of-duties principles and AU-3 audit-record content/minimization considerations. NIST Privacy Framework 1.0 is the current final Privacy Framework while 1.1 remains non-final; its risk-based minimization framing supports keeping Person/worker values outside this organizational change envelope. RFC 9562 defines UUIDv4 and UUIDv7 and supports preserving the HRIS owner's operational UUID evolution while using UUIDv4 for leaf-owned random correlation references. These sources inform design controls; they are not certification or legal-compliance claims.

## Decision

Add `PositionReportingChangeReviewPacket` as a bounded pre-mutation evidence contract that:

1. binds one authoritative tenant plus subordinate, current-manager and proposed-manager Position references without copying Person identity or worker values;
2. binds `effective_on` as business time and `recorded_at` as a separately canonicalized system-recorded evidence instant;
3. binds exact Position-scope and organization-scope SHA-256 evidence plus a controlled reporting-change reason and explicit evidence version;
4. requires requester/reviewer reference inequality as an early guard but still requires authoritative actor resolution before mutation;
5. rejects subordinate=current manager, subordinate=proposed manager and current=proposed manager to prevent self-reporting and no-op evidence;
6. keeps `review_state=requires_human_review`, `scope_verification_state=requires_authoritative_resolution`, `mutation_state=not_authorized_to_apply`, and `decision_authority=human_review_only` immutable;
7. requires the host, immediately before mutation, to re-resolve all three Position records and the current solid-line relationship in the exact tenant and bitemporal coordinate, prove Position validity/staffability, authoritative reviewer separation, no cycle and no multiple visible solid-line managers, and then produce immutable audit/outbox evidence; and
8. performs no database mutation, no cross-service application-table SQL, no identity-provider write and no autonomous employment decision.

Operational HRIS-owned UUIDs remain canonical non-sentinel UUIDs rather than being narrowed to UUIDv4. Packet-owned change/actor correlation references require canonical UUIDv4. The package uses a process-local creation seal only to detect in-process post-construction evidence mutation; durable reference uniqueness and durable immutability remain responsibilities of authoritative persistence/audit boundaries.

## Consequences

A buyer can inspect and hash a minimally identifying, human-review-only reporting reassignment before any organizational truth changes. The packet explicitly separates review evidence from mutation authority and makes the next authoritative checks visible instead of implying that identifier syntax proves organizational validity.

The deliberate limitation is that the packet cannot establish that the current reporting relationship exists, that the proposed manager is valid at the requested date, that the change is policy/legal compliant, or that persistence succeeded. Those claims require authoritative runtime evidence after the relevant HRIS capability is integrated.

## References

See `docs/doctoring/position-reporting-change-review-references.md`.
