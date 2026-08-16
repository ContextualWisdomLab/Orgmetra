# Test Strategy

## Canonical coverage gate

This document is the canonical owned-code coverage requirement. Every production implementation must achieve 100% statement and 100% branch coverage where its pinned toolchain exposes those metrics. An unmet threshold fails CI. Generated code, vendored code, migrations that cannot be instrumented, and declarative schemas require explicit contract or execution tests rather than silent exclusion.

The current foundation pack is executable documentation. Its validation command is:

```text
npm run validate
```

The command must fail on a missing required artifact, manifest mismatch, invalid database name, reversed temporal interval contract, missing append-only guard, incomplete high-risk OpenAPI context, empty OpenID Connect scope requirement, internal trace identifier in a client error schema, unbalanced Markdown fence, or incomplete Apache-2.0 license.

## Foundation test matrix

| Evidence | Execution command |
|---|---|
| Required artifacts, manifest SHA-256/byte/line integrity, package metadata, Markdown, license, and database naming | `npm run validate` |
| PostgreSQL DDL, period constraints, append-only triggers, and 3NF relationships | `postgresql-test-container --migration database/migrations/0001_foundation_schema.sql` once the implementation harness lands |
| OpenAPI 3.2 authentication, non-empty operation scopes, mutation headers, request schemas, evidence requirements, and client-safe error references | `openapi-contract-test schemas/openapi.yaml` once the generated server harness lands |
| Tenant/actor/purpose authorization matrix and negative high-impact commands | service-specific unit and integration test commands recorded in each service package |
| AsyncAPI/CloudEvents envelope compatibility | provider and consumer contract test commands recorded beside the versioned event schema |
| External adapter timeout, malformed response, tenant mismatch, and unavailable-state handling | fake-server tests in each adapter package |
| Role-workspace keyboard, focus, exact-value, permission-denied, and confirmation states | Storybook interaction/a11y tests plus browser E2E for the owning workspace |

Future service packages must publish their exact test, statement-coverage, branch-coverage, docstring, typecheck, and build commands in the package manifest and CI log.

## High-impact decision tests

Required negative and provenance tests include:

- an LLM or orchestration credential cannot create a selection-decision record;
- an LLM or integration adapter cannot transition `Candidate` to `Offered` or `Offered` to `Worker`;
- missing or insufficient Keyverse scope, actor, tenant, purpose, reason, confirmation, evidence reference, or evidence version fails closed;
- a reused confirmation or idempotency key cannot bind to different command content;
- previewed evidence versions must equal recorded evidence versions;
- record and audit append either complete together or leave no authoritative decision;
- a cross-tenant read or mutation is denied and produces a bounded audit event;
- a purpose header cannot enlarge a token's operation scope; and
- client errors contain an actionable `next_action` and random `support_reference` but no internal trace/span identifier, topology, tenant identifier, or PII.

## External psychometric contracts

Orgmetra does not combine fast-mlsirm and TEPP into one dependency.

### fast-mlsirm

- Canonical repository: `ContextualWisdomLab/fast-mlsirm`.
- Reviewed immutable revision for this baseline: `fb67ced09d8ee00542c05d56374537a9a7239751`.
- Orgmetra contract identifier: `orgmetra.fast_mlsirm.v1`.
- Owner: `workforce_validation`; the normal online path consumes a Psychometrics Commons immutable result snapshot rather than calling the kernel from a role workspace.
- Backend: Rust production arithmetic with bounded CPU multithreading and GPU parity for material kernels. NumPy is a reference/parity path only.
- Request/result contract: versioned model identifier, response-snapshot reference, seed manifest, backend, precision, estimates, uncertainty, diagnostics, convergence, and provenance digest.
- Failure semantics: bounded timeout, typed unavailable/invalid/nonconverged result, no partial score publication, and no invented fallback estimate.

### TEPP

- Canonical repository: `ContextualWisdomLab/TEPP`.
- Reviewed immutable revision for this baseline: `40adac9a26a8af85147ffa2795fb548ea243e0e5`.
- Orgmetra contract identifier: `orgmetra.tepp.v1`.
- Owner: `workforce_validation`.
- Backend: Rust temporal/event/multilevel analysis services and immutable analytical artifacts.
- Request/result contract: tenant-scoped evidence references, event/effective/available times, knowledge cutoff, multiple-membership weights, model manifest, uncertainty, leakage audit, and provenance digest.
- Failure semantics: bounded timeout, typed invalid-temporal-order/insufficient-evidence/nonconverged/unavailable result, and no promotion of an analytical artifact to HRIS truth.

### Psychometrics Commons snapshot linkage

- Canonical repository: `ContextualWisdomLab/psychometrics-commons`.
- Reviewed immutable revision for this baseline: `cc5850a0d1eacbbf16d03075534fce460a8286e6`.
- Orgmetra stores the immutable `snapshot_ref`, instrument/model version, scoring-contract version, event count, payload digest, result artifact reference, and provenance reference.
- A snapshot may be consumed only when tenant, session, instrument version, event prefix, digest, and result identity all match.

Before production integration, each contract requires:

- schema compatibility tests against the immutable revision;
- fake-server timeout, malformed result, unavailable, and tenant-mismatch tests;
- exact replay and provenance-link tests;
- fast-mlsirm Rust/NumPy and CPU/GPU parity evidence where supported;
- TEPP CPU/GPU parity for material kernels and leakage-safe temporal replay;
- upgrade tests proving a new revision cannot silently change a pinned result schema.

## Psychometric and mathematical evidence

Any Orgmetra-owned or integrated model must provide evidence appropriate to its structure:

- true-parameter recovery;
- bias, MAE, and RMSE;
- interval coverage;
- convergence and failure-rate evidence;
- deterministic replay under a recorded seed manifest;
- CPU/GPU parity where material;
- multilevel, longitudinal, and temporal recovery where relevant; and
- cross-classified multiple-membership recovery using known membership weights, including bias/MAE/RMSE, interval coverage, and convergence.

A model that omits evidence for a structural feature it uses is not eligible for a production decision workflow.

## UI tests

- Keyboard navigation and visible focus.
- Accessible names, roles, states, and error association.
- Exact-value table for every chart.
- Permission-denied and Keyverse-unavailable states.
- High-risk review, confirmation, recording, and audit states.
- Narrow viewport, 200% zoom/reflow, reduced-motion, and high-contrast review.
