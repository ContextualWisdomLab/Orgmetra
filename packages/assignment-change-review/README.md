# Orgmetra Assignment Change Review

`orgmetra-assignment-change-review` is a transport-neutral pre-mutation governance contract for internal assignment changes. It lets an HR workflow correlate one worker's current authoritative Employment/Assignment/Job/Position scope with a proposed Job/Position allocation, reviewed allocation policy, worker-impact evidence, and a communication plan without copying worker values into the review envelope.

## What the packet binds

The packet requires an authoritative Orgmetra `tenant_record_id` satisfying the protected-core canonical non-sentinel operational-UUID contract plus opaque canonical non-sentinel UUIDv4-backed references for the Person, Employment, current Assignment, current Job and Position, proposed Job and Position, current-scope snapshot, reviewed workforce-allocation plan, exact workforce-allocation policy, worker-impact assessment, communication plan, requester, and reviewer. Packet-owned namespaced trust references reject UUIDv1 and other UUID versions so timestamp/node correlation metadata cannot enter leaf-owned opaque references. Each trust-bearing evidence artifact is paired with a lowercase SHA-256 digest. A bounded positive `evidence_version` is part of canonical evidence so actor/purpose/reason evidence from different review-contract revisions cannot silently collide.

`requested_effective_on` is review intent, not proof that the date is valid or authorized. `generated_at` is system-recorded issuance evidence: construction requires an exact built-in `datetime`, resolves one concrete caller timezone offset, converts the instant to a built-in UTC `datetime`, rejects future instants, and stores only that detached UTC value. Later canonical export therefore never invokes the caller's original `tzinfo`; mutable/stateful timezone providers cannot rewrite already-issued evidence. Missing offsets, provider exceptions, UTC-normalization overflow, datetime subclasses, and low-level reinjection of a non-UTC timestamp fail closed before evidence emission.

A frozen dataclass alone is not immutable issuance evidence because low-level Python mutation and allocator bypass can still create or rewrite otherwise valid packet-shaped objects. Normal `AssignmentChangeReviewPacket(...)` construction therefore arms one context-local allocator ticket; the exact packet `__new__()` invocation consumes that ticket immediately, before field validation or caller-owned timezone code can execute, and binds constructor eligibility only to that exact live object. Direct `object.__new__`, direct packet-allocator calls, and allocator calls reached reentrantly from `tzinfo.utcoffset()` do not receive or retain constructor provenance and cannot later copy valid fields, invoke `__post_init__()`, and mint a second issued packet. Successful construction then binds the exact canonical JSON to a process-local HMAC seal stored outside packet-writable slots and records the exact live identity as issued. Issuance registration is single-use for the same live packet identity, so re-entering `__post_init__()` cannot replace the authoritative seal after a valid-value rewrite. `canonical_json()` requires that exact issued identity, snapshots the current canonical bytes once, verifies that exact snapshot against the external issuance seal, and returns the verified bytes without rereading packet fields. A valid-value rewrite, allocator-bypassed reconstruction, attempted seal renewal, or missing process-local issuance evidence fails closed. These context/identity/HMAC controls are in-process defense-in-depth only; they are not a hostile-interpreter capability boundary, portable signature, rehydration credential, durable cross-process uniqueness mechanism, purpose authorization record, or immutable audit/outbox substitute.

Immediately before approval/mutation, the host must re-resolve **every packet reference within `tenant_record_id`**, specifically resolve `requester_reference` and `reviewer_reference` through the authoritative actor boundary and prove their resolved identities are distinct, verify the Person-to-Employment-to-current-Assignment binding and current Assignment/Job/Position worker scope, and then resolve the proposed relationships against authoritative bitemporal Orgmetra records. Canonical JSON and the packet SHA-256 provide immutable correlation evidence only after issuance-seal verification.

## Fail-closed governance

The packet always remains value-minimized and pre-mutation:

- Person identity is sensitive correlating metadata even when represented by an opaque reference.
- Person PII, compensation values, numeric allocation values, and free-form model output are not fields in the envelope.
- Requester and reviewer references must differ as an early syntactic guard; reference inequality is not authoritative separation-of-duties evidence.
- `purpose_code` is fixed to `assignment_change_review`.
- `reason_code` is limited to reviewed non-sensitive categories: `internal_reassignment`, `workforce_reallocation`, `temporary_detail`, `position_reclassification`, or `organizational_realignment`; free-form personal reasons belong outside this packet.
- `evidence_version` is a positive integer included in canonical JSON and the packet digest.
- Human confirmation is mandatory; decision authority remains `human_review_only`.
- `scope_verification_state` remains `requires_authoritative_resolution`.
- `mutation_state` remains `not_authorized_to_apply`.
- Direct construction and `dataclasses.replace(...)` are revalidated, while allocator-bypassed objects have no constructor provenance; callers cannot manufacture an approved/applied or newly issued packet outside the governed construction path.

## Next action

Before mutation, re-resolve every packet reference in the exact `tenant_record_id` context; prove requester/reviewer resolve to distinct authoritative actor identities; verify the Person-to-Employment-to-current-Assignment binding and current Assignment/Job/Position worker scope; verify proposed Position-to-Job binding and capacity; check the requested effective date; and verify the exact bound workforce-allocation policy, worker-impact evidence, and communication-plan provenance. Record accountable human approval, then apply the change only through Orgmetra's authoritative People mutation boundary. This package does not write HRIS tables and does not bypass purpose-bound authorization, idempotency, immutable audit/outbox, or bitemporal invariants.

## Standards boundary

The design is informed by ISO 30201:2026 HR management-system requirements, ISO 30434:2023 workforce-allocation guidance, ISO 30435:2023 workforce-data-quality guidance, and the U.S. OPM Guide to Processing Personnel Actions as a jurisdiction-specific example of documented, effective-dated personnel-action approval. These sources do not make the packet certified or legally sufficient in any jurisdiction; the authoritative host owns applicable policy and legal checks.
