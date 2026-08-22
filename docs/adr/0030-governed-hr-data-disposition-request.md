# ADR-0030: Govern HR data disposition as a non-authorizing execution request

- **Status:** Proposed on active stacked PR
- **Date:** 2026-08-22

## Context

A retention review can establish that a reviewed due date has elapsed, but an elapsed date is not destructive authority. A commercial HRIS also needs to preserve legal-hold state, scope, actor separation, policy provenance, and an immutable decision trail before any later delete or pseudonymize operation can be approved. At the same time, application-layer data disposition is not equivalent to storage-media sanitization.

## Decision

Orgmetra will represent the next lifecycle step as a value-minimized `HrDataDispositionExecutionRequest` rather than an executable deletion command.

The request must:

1. bind the exact upstream retention-review reference/digest and retention-policy reference/digest;
2. accept only a review strictly after the retained-through due date;
3. require a reviewed clear legal-hold state;
4. require distinct requester and reviewer actors;
5. permit only a closed disposition-action vocabulary;
6. preserve tenant/resource scope with opaque references and no HR payload values;
7. remain `not_authorized_to_execute` and require authoritative scope/actor/policy/hold re-resolution plus separate human execution approval;
8. produce deterministic canonical evidence with serialization-time integrity revalidation; and
9. record `media_sanitization_state=not_claimed` because storage-media sanitization and its validation belong to the storage/infrastructure owning boundary.

No direct cross-service application-table SQL is permitted. No LLM output can authorize disposition.

## Consequences

- A passed retention date cannot silently become deletion authority.
- Active or stale legal-hold state fails closed before a request exists.
- A future durable executor can be introduced behind a separate purpose-bound authorization, immutable audit/outbox, idempotency, recovery, and human-confirmation boundary without changing the semantics of the review packet.
- Storage sanitization evidence can later be linked through a published contract without Orgmetra making a false sanitization claim.
- This ADR remains active-PR truth until the dependency stack is integrated and all exact-head gates pass together.

## Alternatives rejected

- **Delete automatically when the due date passes:** rejected because policy applicability, holds, authority, and scope can change and require authoritative re-resolution.
- **Let the retention-review packet authorize deletion:** rejected because review evidence and execution authority are separate control planes.
- **Treat an application delete as NIST media sanitization:** rejected because SP 800-88 Rev. 2 defines a broader storage/media sanitization assurance program and validation boundary.
