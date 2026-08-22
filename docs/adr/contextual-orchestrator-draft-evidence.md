# ADR: Govern Contextual Orchestrator output as untrusted draft evidence

- Status: active-PR decision; not protected-main truth until this PR merges
- Date: 2026-08-22
- Owner boundary: Orgmetra
- Foreign dependency: ContextualWisdomLab/contextual-orchestrator, read-only

## Context

Orgmetra needs model-assisted drafting while preserving defensible HR governance. The reviewed Contextual Orchestrator OpenAPI contract provides an authenticated Responses API, and current multi-model orchestration research demonstrates that one visible output may result from dynamic coordination across several worker models. Neither the API contract nor those research results establish that an output is authoritative HR evidence or a permissible employment decision.

## Decision

Orgmetra will consume Contextual Orchestrator only through its published contract and will represent completed model work with a value-minimized `DraftEvidenceEnvelope`.

The envelope binds exact tenant/target scope, request identity, distinct requesting/reviewing actors, an approved non-decision draft use, requested model/orchestration alias, input/response/provenance digests, the reviewed foreign revision and API operation, evidence version, and UTC recorded time. It stores no prompt, model-output text, credentials, candidate/worker PII, or compensation values.

Every envelope is permanently labeled `untrusted_draft`, `requires_human_review`, and `not_authorized_for_employment_decision`. A downstream mutation or high-impact decision must perform its own authoritative actor, purpose, scope, evidence-version, and human-confirmation checks. The envelope can correlate immutable audit/outbox evidence but cannot authorize action.

Trust-bearing runtime values are exact built-in primitives; the envelope runtime type is final; canonical serialization revalidates fields and verifies a process-local creation seal to reject ordinary replacement and post-construction rewriting.

## Consequences

Adaptive orchestration can evolve independently behind Contextual Orchestrator without forcing Orgmetra to copy Fugu-, Conductor-, or TRINITY-like routing logic. Orgmetra retains auditable provenance and a stable MSA extraction boundary while treating the foreign service as independently deployable.

Provider/model provenance that is not guaranteed by the reviewed published API must be supplied as captured evidence and represented by digest; Orgmetra does not invent provider facts. The process-local seal is not durable storage integrity; durable evidence remains the responsibility of Orgmetra's immutable audit/outbox persistence.
