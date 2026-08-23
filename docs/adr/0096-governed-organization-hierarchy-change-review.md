# ADR 0096: Govern Organization Unit hierarchy changes before mutation

## Status

Active PR only. This ADR is not protected-main truth until the owning PR is integrated.

## Context

Orgmetra already treats Organization Unit hierarchy as bitemporal HRIS truth. A parent change can alter organizational scope used by reporting, authorization, analytics, and downstream workflows. A reviewed request must therefore remain distinct from the authoritative mutation that changes HRIS truth.

A pre-mutation evidence packet also needs to represent moving an Organization Unit to or from the root without inventing a sentinel parent identifier. It must preserve the requested business-effective date separately from the system-recorded review-evidence time and must not copy Person PII or worker values into durable governance evidence.

## Decision

Introduce a bounded `OrganizationHierarchyChangeReviewPacket` that records only the reviewed change correlation and governance evidence.

The packet:

1. binds one tenant and one Organization Unit to the reviewed current and proposed parent;
2. permits `None` only for a real root attachment/detachment and rejects a no-op where current and proposed parents are equal;
3. rejects self-parenting locally but does not pretend that a leaf packet can prove the full hierarchy is acyclic;
4. keeps `effective_on` separate from `recorded_at`;
5. binds reviewed Organization Unit and hierarchy snapshots by lowercase SHA-256 digest instead of copying HR record values;
6. requires distinct requester and reviewer correlations, one fixed purpose, one controlled reason, and explicit evidence versioning;
7. fixes review/scope/mutation/decision-authority states so the packet can never authorize the mutation itself;
8. rejects caller-defined runtime subclasses at trust-bearing primitive boundaries; and
9. uses deterministic canonical JSON, redacted routine representation, and a process-local issuance digest as defense in depth against post-construction mutation.

The next boundary must re-resolve the Organization Unit, current parent, proposed parent, hierarchy and accountable actors against authoritative same-tenant bitemporal HRIS truth. It must reject stale current-parent evidence, self-parenting, cycles and multiple visible parents, verify the reviewed evidence, and persist the resulting mutation with immutable audit/outbox evidence in the authoritative transaction.

## Identifier ownership

Tenant and Organization Unit identifiers are HRIS-owned operational identifiers. The packet therefore accepts canonical non-sentinel UUID text without freezing them to UUIDv4; UUIDv7 remains interoperable. Packet-owned change references and actor correlations use UUIDv4 opacity. This distinction avoids forcing leaf-package identifier policy onto the authoritative HRIS owner.

## Privacy and security rationale

The packet contains no Person identifier, worker value, compensation, rating, free-form personal reason, credential, or employment-decision authority. Purpose, reason, requester/reviewer separation, immutable correlation evidence and later authoritative audit support separation-of-duties and accountability without claiming certification.

NIST Privacy Framework 1.0 remains the current final Privacy Framework baseline; NIST describes Privacy Framework 1.1 as an Initial Public Draft with the final update still forthcoming. NIST SP 800-53 Rev. 5 Release 5.2.0 is the current finalized minor release used for security/privacy-control context. UUID syntax and version semantics follow RFC 9562.

## Consequences

- Buyers gain an explicit review artifact for organization-structure changes instead of conflating approval evidence with mutation authority.
- Root transitions remain representable without reserved/sentinel parent identifiers.
- The slice stays independently deployable and does not depend on direct cross-service application-table access.
- Process-local tamper detection is defense in depth only; durable uniqueness, authorization, concurrency control, hierarchy validation and audit remain responsibilities of authoritative persistence/orchestration boundaries.
