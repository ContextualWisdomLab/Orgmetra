# Changelog

## 0.1.0 - 2026-08-22

- Added the Orgmetra-owned `DraftEvidenceEnvelope` for value-minimized Contextual Orchestrator provenance.
- Pinned the reviewed foreign API evidence to `contextual-orchestrator@e226e1197bdfc890c9d8e5b9b648c78857d7e465` and `POST /v1/responses` from OpenAPI 0.1.0.
- Required distinct requesting/reviewing actors, explicit non-decision draft uses, immutable provenance digests, evidence versioning, and fail-closed exact runtime primitives.
- Repaired actor privacy by requiring opaque canonical `actor:` UUIDv4 correlations instead of human-readable handles.
- Repaired system-time provenance by generating an init-disabled `recorded_at` and `draft_evidence_reference` at every Orgmetra issuance; callers cannot backdate/future-date system-recorded evidence through constructor input, and dataclass replacement is a visibly new issuance.
- Reframed the process-local HMAC as accidental in-process mutation detection only; durable uniqueness, authorization, immutability, ordering, and tamper evidence remain owned by authoritative immutable audit/outbox persistence.
- Repaired checked-versus-emitted evidence integrity so `canonical_document()` and `canonical_json()` emit the exact payload snapshot whose bytes were validated against the creation-time seal, with no second live-field read after the seal check.
- Marked every model-derived result as untrusted draft evidence requiring human review and carrying no employment-decision authority.
- Added recursive owned docstring inventory, exact 100% owned statement/branch coverage, and clean-checkout quality gating.
- Build a wheel and execute the quality suite against the SHA-256-bound installed artifact in a fully isolated virtual environment; install the reviewed hash-pinned pytest/coverage toolchain inside that environment and fail closed if package or test-tool imports resolve outside it.