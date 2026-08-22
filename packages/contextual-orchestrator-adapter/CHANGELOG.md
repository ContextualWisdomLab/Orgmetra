# Changelog

## 0.1.0 - 2026-08-22

- Added the Orgmetra-owned `DraftEvidenceEnvelope` for value-minimized Contextual Orchestrator provenance.
- Pinned the reviewed foreign API evidence to `contextual-orchestrator@e226e1197bdfc890c9d8e5b9b648c78857d7e465` and `POST /v1/responses` from OpenAPI 0.1.0.
- Required distinct requesting/reviewing actors, explicit non-decision draft uses, immutable provenance digests, exact UTC recorded time, and fail-closed runtime primitives.
- Marked every model-derived result as untrusted draft evidence requiring human review and carrying no employment-decision authority.
- Added exact 100% owned statement/branch coverage and clean-checkout quality gating.
- Build a wheel and execute the quality suite against the SHA-256-bound installed artifact in a fully isolated virtual environment; install the reviewed hash-pinned pytest/coverage toolchain inside that environment and fail closed if package or test-tool imports resolve outside it.
