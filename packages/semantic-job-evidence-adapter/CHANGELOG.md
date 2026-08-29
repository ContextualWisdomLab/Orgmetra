# Changelog

## Unreleased

- Add a value-minimized, human-review-required Semantic Data Portal ontology evidence envelope for Job Analysis.
- Pin the reviewed read-only dependency revision and `POST /ontology/resolve` API operation.
- Bind tenant, Job Analysis scope, accountable actors, source/query/response digests, evidence version, and UTC system-recorded time without copying raw ontology or HR content.
- Require opaque canonical `actor:` UUIDv4 correlations so human-readable actor handles cannot enter durable evidence.
- Fail closed on malformed governance evidence, self-review, caller-defined primitive subclasses, dependency-contract drift, post-construction mutation, seal reset, and runtime type extension.
- Repair the post-issuance integrity path so rewriting a payload together with a recomputed packet-owned seal still fails: the authoritative creation seal is held in a process-local, lock-protected issuance registry outside envelope-writable slots.
- Return the exact canonical payload/JSON snapshot that passed seal verification so an intervening same-process mutation cannot make checked bytes and emitted bytes diverge.
- Document the process-local issuance boundary: copied/restored envelope objects fail closed, while durable audit/outbox persistence stores emitted canonical JSON and evidence digest rather than the live envelope object.
- Bound declared runtime support to Python `>=3.12,<3.15` and execute the installed wheel on Python 3.12, 3.13, and 3.14 before claiming compatibility.
- Add an exact-head quality workflow with exact 100% owned production statement and branch coverage plus clean-checkout enforcement.
- Build a wheel and execute the quality suite against the SHA-256-bound installed artifact in a fully isolated virtual environment; install the reviewed hash-pinned pytest/coverage toolchain inside that environment and fail closed if package or test-tool imports resolve outside it.
