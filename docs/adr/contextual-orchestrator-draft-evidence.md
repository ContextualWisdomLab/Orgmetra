# ADR: Govern Contextual Orchestrator output as untrusted draft evidence

- Status: active-PR decision; not protected-main truth until this PR merges
- Date: 2026-08-22
- Owner boundary: Orgmetra
- Foreign dependency: ContextualWisdomLab/contextual-orchestrator, read-only

## Context

Orgmetra needs model-assisted drafting while preserving defensible HR governance. The reviewed Contextual Orchestrator OpenAPI contract provides an authenticated Responses API, and current multi-model orchestration research demonstrates that one visible output may result from dynamic coordination across several worker models. Neither the API contract nor those research results establish that an output is authoritative HR evidence or a permissible employment decision.

Fresh review also exposed three trust-boundary risks in the first adapter design: human-readable actor handles could enter durable evidence; caller-supplied `recorded_at` could masquerade as system-recorded time; and constructor-visible issuance markers could make a process-local change detector sound stronger than it was.

## Decision

Orgmetra will consume Contextual Orchestrator only through its published contract and will represent completed model work with a value-minimized `DraftEvidenceEnvelope`.

The envelope binds exact tenant/target scope, request identity, a system-generated `draft_evidence:` UUIDv4 issuance correlation, distinct opaque `actor:` UUIDv4 requester/reviewer correlations, an approved non-decision draft use, requested model/orchestration alias, input/response/provenance digests, the reviewed foreign revision and API operation, evidence version, and system-recorded UTC time. It stores no prompt, model-output text, credentials, human-readable actor handles, candidate/worker PII, or compensation values.

`recorded_at` is not an initializer argument. The Orgmetra evidence constructor generates it from the current built-in UTC clock together with the new issuance reference. Caller event/effective time, if later required, must be modeled separately rather than overloading system-recorded time.

Every envelope is permanently labeled `untrusted_draft`, `requires_human_review`, and `not_authorized_for_employment_decision`. A downstream mutation or high-impact decision must perform its own authoritative actor, purpose, scope, evidence-version, and human-confirmation checks. The envelope can correlate immutable audit/outbox evidence but cannot authorize action.

Trust-bearing runtime values are exact built-in primitives and the envelope runtime type is final. A process-local HMAC snapshot detects accidental mutation of one already-created Python object before export. It is not treated as a cryptographic authorization or durable adversarial tamper-prevention control. `dataclasses.replace(...)` is explicitly a new issuance: init-disabled issuance fields are regenerated, so the replacement receives a new evidence reference and new system-recorded time rather than rewriting the original issuance.

## Consequences

Adaptive orchestration can evolve independently behind Contextual Orchestrator without forcing Orgmetra to copy Fugu-, Conductor-, or TRINITY-like routing logic. Orgmetra retains auditable provenance and a stable MSA extraction boundary while treating the foreign service as independently deployable.

Provider/model provenance that is not guaranteed by the reviewed published API must be supplied as captured evidence and represented by digest; Orgmetra does not invent provider facts. Durable uniqueness, authorization, immutability, ordering, and tamper evidence remain the responsibility of Orgmetra's authoritative immutable audit/outbox persistence.
