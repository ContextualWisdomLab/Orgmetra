# ADR — Govern Semantic Data Portal source evidence at the Orgmetra Job Analysis boundary

## Status

Active PR. This document does not describe protected-main truth until the owning PR merges.

## Context

Orgmetra's protected Job Analysis model already distinguishes authoritative human-reviewed evidence from draft/model-derived material, while protected traceability still lists Semantic Data Portal integration as planned. Semantic Data Portal is a separately owned CWL product and publishes ontology-resolution APIs. Direct table access or copying its implementation into Orgmetra would violate the dedicated-writer and modular-service boundary.

Ontology resolution can improve Task/FJA/KSAO evidence discovery, but a semantic match is not itself an authoritative Job-analysis conclusion and must not become an autonomous employment decision. Orgmetra therefore needs a local governance artifact that records exactly what external contract and evidence version were reviewed without storing the raw ontology query/response in the audit correlation object.

## Decision

Orgmetra owns a final, immutable `SemanticJobEvidenceEnvelope` that binds:

1. tenant and Job Analysis scope;
2. an opaque Orgmetra ontology-request reference;
3. distinct requesting and human-reviewing actor references;
4. the closed use `job_analysis_source_evidence`;
5. SHA-256 digests for query-term evidence, response evidence, and source-catalog state;
6. the reviewed Semantic Data Portal revision `e48aa13c4af7a4875d4b53e6a60b50405c265a2f` and `POST /ontology/resolve` operation;
7. evidence version and exact UTC system-recorded time.

The canonical evidence always records `external_source_evidence`, `requires_human_review`, and `not_authorized_for_job_or_employment_decision`.

Semantic Data Portal remains read-only to this Orgmetra lane. No foreign application table is queried. Provider revision/API drift fails closed until explicitly reviewed. Raw ontology content, PII, credentials, scores, and decisions stay outside this value-minimized envelope.

Trust-bearing runtime primitives are accepted only as exact built-in types before caller-overridable equality, hashing, comparison, parsing, or serialization can run. Creation-time evidence is sealed in process and is revalidated before canonical export so valid-looking post-construction rewrites fail closed.

## Consequences

- Buyers can trace a Job Analysis source claim to an exact external contract revision and evidence digests without treating that source as authoritative by syntax alone.
- Human review remains explicit and separable from source retrieval.
- A future Semantic Data Portal contract change requires an Orgmetra review/update rather than silently changing evidence semantics.
- This slice does not implement network transport, foreign retries, foreign authorization, raw ontology storage, Job Analysis approval, or employment decisions.
- The approach is compatible with W3C provenance principles: source entities and activities remain externally owned while Orgmetra records bounded provenance needed for its own evidence chain.

## Verification

The package quality lane requires exact-current-head tests, exact 100% owned production statement and branch coverage, adversarial runtime-integrity regressions, and a clean checkout. Repository-level Foundation/SAST/Security/Recovery evidence remains separately required by live merge governance.
