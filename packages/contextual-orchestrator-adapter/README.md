# Contextual Orchestrator adapter

This package is Orgmetra's value-minimized evidence boundary for model-assisted drafts produced through the published Contextual Orchestrator contract. It does **not** execute inference, store credentials, read another service's application tables, or grant employment-decision authority.

## What the envelope proves

`DraftEvidenceEnvelope` binds one tenant and Orgmetra target to:

- an opaque orchestration-request reference;
- distinct requesting and human-reviewing actors;
- one approved draft use;
- the requested model or orchestration alias;
- SHA-256 digests for the input evidence, response evidence, and captured provenance evidence;
- the exact reviewed Contextual Orchestrator source revision and `POST /v1/responses` contract;
- an evidence version and exact UTC system-recorded timestamp.

The canonical document always records `output_trust_state=untrusted_draft`, `review_state=requires_human_review`, and `decision_authority_state=not_authorized_for_employment_decision`. Those are governance facts, not UI labels. A downstream employment action must re-enter its own authoritative human-confirmation boundary.

## What the envelope deliberately does not contain

Do not put prompts, source documents, candidate or worker PII, compensation values, credentials, or model-output text into this evidence object. Store authorized business content in its owning HR boundary and bind only opaque references and digests here.

The process-local creation seal detects ordinary dataclass replacement and post-construction object rewriting before canonical evidence leaves this adapter. Durable tamper evidence remains the responsibility of Orgmetra's immutable audit/outbox persistence after `canonical_json()` and `evidence_digest()` are emitted.

## Dependency boundary

The reviewed foreign dependency is `ContextualWisdomLab/contextual-orchestrator@e226e1197bdfc890c9d8e5b9b648c78857d7e465`. Its published OpenAPI 0.1.0 exposes authenticated `POST /v1/responses` with required `model` and `input`. Orgmetra consumes that published contract only; Contextual Orchestrator remains independently deployable and read-only from this writer lane.

Research on TRINITY, Conductor, and Sakana Fugu supports treating adaptive multi-model orchestration as a capability pattern. It does not establish validity, fairness, or safety for employment decisions. Orgmetra therefore records provenance and keeps all model-derived output as untrusted draft evidence pending accountable human review.
