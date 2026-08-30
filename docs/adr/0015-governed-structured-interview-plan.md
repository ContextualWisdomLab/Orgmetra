# ADR 0015: Govern structured-interview plans as candidate-neutral evidence

- **Status:** Proposed — active PR only
- **Date:** 2026-08-18

## Context

Orgmetra already separates authoritative Job/Position/Assignment truth, governed requisition review, selection evidence, and accountable human employment decisions. A buyer still needs a defensible boundary between an approved opening and the interview that will be used as a selection procedure.

A structured interview is stronger when assessed competencies come from current job analysis, candidates receive the same predetermined questions, and responses are evaluated against common rating standards. A question count cannot prove that each governed competency is represented, so the approved question-to-competency mapping needs its own immutable evidence identity. Candidate identity, assessment values, and semantic/value-bearing labels are unnecessary at this pre-use boundary and would increase privacy risk. Packet-owned trust references therefore use UUIDv4; the authoritative tenant identifier instead follows Orgmetra core's canonical non-sentinel operational UUID contract.

Opaque identities and artifact digests identify evidence but do not prove tenant ownership, requisition-to-Job-to-job-analysis relationships, or distinct human identities. Those relationships must be re-resolved at authoritative owner boundaries immediately before activation. A prose-only `next_action` is insufficient: the package needs an executable host boundary that cannot issue activation evidence when authoritative checks reject or when returned verification evidence belongs to another plan, actor, or approval instant.

Plan-generation time and approval time are trust-bearing evidence. Caller-controlled mutable timezone state must not make one governed instant later represent a different UTC instant. Caller-owned `tzinfo` implementations are executable code and may raise arbitrary exceptions while `utcoffset()` is evaluated; such failures and unrepresentable UTC normalization must become field-specific governed validation before plan issuance, authority side effects, verification acceptance, or canonical export. Constructor provenance must also not remain ambient while such caller code runs: otherwise a reentrant timezone callback can invoke the plan allocator, retain a second object that inherits constructor eligibility, populate it later with otherwise valid fields, and mint issuance evidence without a normal class construction.

Python `frozen=True` is not an adversarial immutability or authorization boundary. `object.__setattr__` can rewrite dataclass fields, and low-level allocation can create a dataclass-shaped instance without completing its governed constructor. Merely executing a class `__new__` method is also not proof of construction because callers can invoke that allocator directly. A module-private constructor token is still reachable by Python callers. Therefore receipt shape construction must not itself confer human-approval authority, and plan issuance must prove that the exact live object entered through the normal full `StructuredInterviewPlan(...)` construction path before `__post_init__` may register creation evidence. Plan construction may register process-local integrity evidence because construction is the governed plan-issuance boundary, but activation-receipt issuance evidence must be registered only by the verified activation factory after authoritative host checks and exact-scope matching have completed.

## Decision

Add a transport-neutral `StructuredInterviewPlan` value object that binds:

- canonical non-sentinel Orgmetra tenant identity and one UUIDv4-backed opaque interview-plan reference;
- UUIDv4-backed requisition and authoritative Job references;
- exact job-analysis, question-set, question-to-competency mapping, and rating-anchor references plus independent SHA-256 digests;
- sorted, unique job-related competency references and a bounded 2–8 actor interviewer panel;
- a bounded question count at least as large as the governed competency count, while the separately bound mapping artifact supplies actual coverage evidence; and
- fixed purpose `structured_interview_plan`, closed reason `approved_requisition_interview`, bounded positive `evidence_version`, precision-preserving UTC time, mandatory human confirmation, and `requires_human_approval` state.

`tenant_record_id` follows the authoritative operational UUID contract. Packet-owned trust-bearing references require canonical non-sentinel UUIDv4 plus their expected namespace. Names, labels, compensation/protected-attribute values, and other semantic suffixes fail closed. Direct construction, builder construction, and `dataclasses.replace(...)` share the same plan validation. `evidence_version` is serialized canonically and changes immutable SHA-256 correlation when revised. Routine plan representation is fully redacted.

Before plan issuance evidence is registered, detach caller-owned `generated_at` into one built-in UTC `datetime` using one concrete offset read from the original aware value. Treat offset evaluation as an untrusted-code boundary: exceptions and offset arithmetic beyond Python's representable `datetime` range become the same field-specific `ValueError`. Store the built-in UTC snapshot rather than caller-owned `tzinfo` state. Canonical timestamp rendering reuses this fail-closed detachment.

A private metaclass arms a context-local **one-shot allocator ticket** immediately before the normal `StructuredInterviewPlan(...)` class construction. The exact `StructuredInterviewPlan.__new__()` invocation consumes that ticket before any field validation, `tzinfo.utcoffset()` call, or other caller-controlled callback can execute, then records construction eligibility only for that exact live object. Successful `__post_init__()` requires and consumes that provenance, computes a process-local HMAC over the canonical plan payload, registers the seal outside plan-writable slots, and records the exact identity as issued. Registration remains single-use for one live plan identity. `canonical_json()` requires exact issued-identity membership plus creation-bound HMAC evidence and uses constant-time comparison before returning bytes; `sha256_digest()` is downstream. An `object.__new__` clone, direct `StructuredInterviewPlan.__new__(StructuredInterviewPlan)` allocation, or allocator call reached reentrantly from caller-owned timezone code cannot call `__post_init__()` to mint fresh issuance evidence because none receives or retains the already-consumed constructor ticket. Low-level mutation, copied/reconstructed identities, missing issuance evidence, and attempted plan resealing fail closed. These context/identity/HMAC controls are same-process integrity evidence only, not a hostile-interpreter capability boundary, persisted signing scheme, portable signature, or replacement for immutable audit/outbox evidence.

Make authoritative activation executable through `StructuredInterviewActivationAuthority` and `activate_structured_interview_plan(...)`. Before authority work, activation requires the exact governed `StructuredInterviewPlan` runtime type, obtains creation-bound canonical plan JSON, derives tenant/interview-plan scope and SHA-256 from those bytes, detaches caller-owned `approved_at` into built-in UTC, validates the approving actor, and rejects chronology before plan generation. The authority receives only detached canonical plan JSON, its exact digest, approving actor, and normalized approval instant—never the live plan object. A retained alias therefore cannot change what the authority reviews through a temporary change-and-restore cycle; non-restored mutation is still rejected by the post-authority plan integrity check.

Implement `StructuredInterviewActivationVerification` as an exact `NamedTuple` carrying tenant, interview-plan reference, plan digest, approving actor, authority-evidence reference/digest, and reviewed `approved_at`. Activation rejects subclasses, unpacks the exact tuple once, normalizes returned approval time through the same fail-closed UTC helper, validates returned values, and compares the complete tenant/plan/digest/actor/time scope against the pre-call request.

`StructuredInterviewActivationReceipt` is a value-minimized receipt shape, not an authorization primitive. Its dataclass constructor validates tenant/reference/digest/time/fixed-governance values but **does not register issuance evidence**. Direct construction and `dataclasses.replace(...)` therefore produce unissued values whose `canonical_json()` and `sha256_digest()` fail closed. The constructor has no issuance-token parameter; a module-private legacy sentinel confers no authority and is retained only as a regression target proving that callers cannot mint issued receipts by importing a private module attribute.

Only after `activate_structured_interview_plan(...)` has accepted exact verification evidence, normalized the returned approval instant, validated all returned fields, and matched tenant, interview-plan reference, plan digest, approving actor, and approval time does it construct the receipt and register a process-local HMAC seal over that exact canonical payload. Issued receipt canonical export recomputes and constant-time compares the seal. Any low-level post-issuance rewrite or missing issuance evidence fails closed. The seal is same-process integrity evidence only; it is not a durable signing key, portable attestation, cross-process rehydration credential, or substitute for the host's immutable audit/outbox record.

The issued receipt records the exact plan digest, accountable UUIDv4 approving actor, authority-verification reference/digest, fixed purpose `structured_interview_activation`, fixed reason `human_approved_plan_activation`, bounded positive evidence version, detached precision-preserving UTC approval time, `human_confirmation=True`, and fixed `approved_for_use` state. Routine receipt and verification representations are fully redacted. The plan and receipt remain candidate-neutral: they contain no candidate identity, response, score, demographic attribute, compensation value, free-form model output, provider credential, or final selection recommendation.

## Consequences

### Positive

- Buyers can prove which Job Analysis, competencies, questions, mapping, rating anchors, panel, and evidence revision were reviewed before candidate use.
- Caller-controlled timezone failures and mutable timezone state cannot silently redefine governed plan or approval instants.
- Constructor-bypassing `object.__new__` clones, direct class-allocator calls, and reentrant allocator calls from caller-owned timezone callbacks cannot mint creation-bound plan issuance evidence merely by copying valid fields and invoking `__post_init__()`.
- The authoritative adapter reviews detached creation-bound plan evidence rather than a caller-owned live plan object.
- Authority verification fields are tuple-immutable at runtime and exact-type checked before one-time unpacking.
- A caller cannot mint an `approved_for_use` evidence artifact by importing a private constructor sentinel: direct and replaced receipt values remain unissued and cannot export canonical evidence.
- Receipt issuance is causally ordered after authoritative host verification and exact tenant/plan/digest/actor/time matching.
- Post-issuance receipt mutation and missing process-local issuance evidence fail closed before canonical export.
- Candidate PII and assessment values remain outside planning and activation artifacts.
- The authority protocol preserves standalone operation and later MSA extraction without cross-service application-table SQL or duplicated foreign-service state.

### Costs and constraints

- The package does not persist requisitions, Job Analysis, interview questions/mappings, responses, scores, or authoritative relationship-resolution results.
- The authority protocol is not proof that a concrete production adapter performs tenant/database/API checks correctly; production adapters still need executable integration evidence and immutable authority/audit records.
- Plan and activation-receipt HMAC seals and live-identity provenance exist only for the lifetime of their in-process objects. They are not portable signatures, durable verification credentials, or key-management facilities.
- Directly constructed receipt values are intentionally unusable as authoritative evidence until a supported future rehydration/issuance contract exists.
- Human approval remains mandatory; model output cannot activate or approve the plan.
- UUID/digest metadata and reference inequality do not establish tenant ownership, identity separation, scientific validity, fairness, or legal compliance.
- This ADR remains proposed until its exact PR head merges into protected `develop`.

## References

See `docs/doctoring/structured-interview-plan-references.md`.
