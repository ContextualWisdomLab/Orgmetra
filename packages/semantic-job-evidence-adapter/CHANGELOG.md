# Changelog

## 0.1.0 — active PR

- Add a value-minimized, human-review-required Semantic Data Portal ontology evidence envelope for Job Analysis.
- Pin the reviewed read-only dependency revision and `POST /ontology/resolve` API operation.
- Bind tenant, Job Analysis scope, accountable actors, source/query/response digests, evidence version, and UTC system-recorded time without copying raw ontology or HR content.
- Fail closed on malformed governance evidence, self-review, caller-defined primitive subclasses, dependency-contract drift, post-construction mutation, seal reset, and runtime type extension.
- Repair the post-issuance integrity path so rewriting a payload together with a recomputed packet-owned seal still fails: the authoritative creation seal is held in a process-local, lock-protected issuance registry outside envelope-writable slots.
- Add an exact-head quality workflow with exact 100% owned production statement and branch coverage plus clean-checkout enforcement.
- Build a wheel and execute the quality suite against the SHA-256-bound installed artifact in a fully isolated virtual environment; install the reviewed hash-pinned pytest/coverage toolchain inside that environment and fail closed if package or test-tool imports resolve outside it.
