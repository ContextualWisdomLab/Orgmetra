# ADR 0092: Governed performance-goal plan activation evidence

Status: **proposed in active PR #92; not protected-main truth until merged**.

## Context

Orgmetra protected main separates performance cycles and criterion observations, but it does not yet provide a governed boundary for activating a worker goal plan. Performance goal content is operational HR data and must remain usable under purpose-bound authorization; it should not be copied wholesale into long-lived governance evidence. Goal-plan existence must also never be treated as an autonomous performance rating or employment decision.

## Decision

Introduce a transport-neutral `PerformanceGoalPlanPacket` that binds tenant, Employment, Job, performance cycle, exact goal-set and measurement-definition SHA-256 provenance, reviewed feedback cadence, distinct requester/reviewer actors, evidence version and system-recorded time.

The packet excludes goal text, ratings, assessment scores, compensation values and employment decisions. It remains fixed to `requires_human_review`, `not_authorized_for_performance_rating`, and `not_authorized_for_employment_decision`. Packet-owned and local actor references use opaque UUIDv4 identifiers; authoritative HRIS Employment, Job and performance-cycle references accept canonical non-sentinel operational UUIDs so Orgmetra does not impose a UUIDv4 restriction on core identities.

A process-local live-reference and creation-digest registry is defense in depth against in-process `dataclasses.replace` rebinding and `object.__setattr__` rewriting. Durable uniqueness and immutability remain responsibilities of authoritative persistence plus audit/outbox transactions.

## Consequences

Authorized product surfaces can keep exact goal content outside this evidence envelope while still proving which reviewed goal set, measurement definition and feedback cadence were activated. Future performance-review logic may reference this plan evidence, but must separately collect criterion outcomes, human judgment and decision evidence. No automated performance or employment decision is introduced by this ADR.
