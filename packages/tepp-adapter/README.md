# Orgmetra TEPP adapter

`orgmetra-tepp-adapter` is Orgmetra's fail-closed pre-transport boundary for TEPP analysis-run request contract v1. It lets an authorized workforce-validation host bind an Orgmetra validation study, accountable actor, immutable analytical snapshot evidence, temporal cutoff, and idempotency evidence to the exact field shape published by TEPP without reading TEPP tables or copying TEPP implementation code.

## Current maturity

This package is **active-PR Orgmetra code**. It does not make TEPP HTTP service availability a shipped fact. The reviewed TEPP protected revision is `7c29e7c971d7940e1fb3def1ed3aae2d1bc8ad4a`; at that revision TEPP publishes `AnalysisRunRequest` v1 as a Rust wire DTO, while its API documentation explicitly says protected main is not yet a production HTTP service. Therefore this adapter creates a governed request packet and deterministic request digest but performs no network transport.

## Contract

`TeppAnalysisRequestPacket.tepp_request()` emits exactly seven TEPP v1 fields: `contract_version`, `idempotency_key`, `tenant_workspace_id`, `snapshot_id`, RFC 3339 `knowledge_cutoff`, `model_contract_version`, and `output_profile`. Unknown Orgmetra governance fields never enter the foreign body because TEPP's DTO is fail-closed on unknown fields.

The packet additionally binds, on the Orgmetra side, the authoritative canonical non-sentinel operational tenant UUID, opaque UUIDv4 validation-study and actor references, an independent SHA-256 snapshot digest, evidence version, generation instant, reviewed TEPP revision, and a digest of the exact TEPP request body. Timezone-aware knowledge and generation values are detached to exact UTC datetimes at construction, so caller-owned timezone providers cannot rewrite request or governance evidence later. Same-key exact retries are distinguishable from same-key semantic conflicts before transport. The tenant identifier follows the protected Orgmetra core identity contract rather than imposing a duplicate UUID-version policy; packet-owned trust references remain UUIDv4-constrained.

## Privacy and authority

Opaque actor, study, workspace, and snapshot correlations remain linkable personal/governance data, so the packet declares `contains_personal_data=true`; it does **not** claim anonymity. Direct identity values, source text, credentials, free-form case narrative, or model output are not accepted by this boundary. The packet representation is fully redacted.

Model-contract and output-profile strings are syntax-constrained machine codes only; syntax is not authority. Immediately before any transport the host must re-resolve the exact tenant, validation study, accountable actor, TEPP workspace/snapshot binding, snapshot digest, model contract, output profile, purpose authorization, and contract compatibility. Any TEPP/LLM result remains untrusted analytical evidence and cannot autonomously make a high-impact employment decision.

## Idempotency

Persist the packet's `idempotency_key`, `request_digest()`, and `governance_scope_digest()` together in Orgmetra's authoritative audit/outbox transaction before a future executable transport is enabled. An exact retry has the same key, request digest, and governance-scope digest. Reusing the key with a different request or governance digest is a conflict and must fail closed. This package exposes comparison helpers but does not invent a second persistence store.

## Test

```bash
PYTHONPATH=packages/tepp-adapter/src \
python -m pytest -c packages/tepp-adapter/pyproject.toml packages/tepp-adapter/tests
```

The package quality gate requires exact 100% owned production statement and branch coverage.
