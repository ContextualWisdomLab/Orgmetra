# Test Strategy

## Canonical coverage gate

This document is the canonical owned-code coverage requirement. Every production implementation must achieve 100% statement and 100% branch coverage where its pinned toolchain exposes those metrics. An unmet threshold fails CI. Generated code, vendored code, migrations that cannot be instrumented, and declarative schemas require explicit contract or execution tests rather than silent exclusion.

The current foundation pack is executable documentation. Its validation command is:

```text
npm run validate
```

The command runs Python repository-integrity validation, the dependency-free Node foundation validator, Node regression tests, and mutation-style OpenAPI operation-contract tests. It must fail on a missing required artifact, manifest mismatch, invalid database name, missing tenant/evidence/audit/temporal DDL contract, incomplete high-risk OpenAPI operation context, empty OpenID Connect scope requirement, internal trace identifier in a client error schema, explicit unfinished-work marker, unbalanced Markdown fence, or incomplete Apache-2.0 license. Ordinary explanatory prose may contain words such as `placeholder`; only explicit TODO/TBD/FIXME marker forms are treated as unfinished work.

## Foundation test matrix

| Evidence | Execution command |
|---|---|
| Required artifacts, manifest SHA-256/byte/line integrity, package metadata, Markdown, license, database naming, tenant/evidence/audit/dispatcher DDL fragments | `npm run validate` |
| Structural OpenAPI 3.2 operation ownership: exact scopes, mutation headers, request-schema binding, evidence requirements, human confirmation, creation `Location` headers, required response codes, and client-safe error fields | `node --test tests/openapi-contract.test.mjs` (also included in `npm run validate`) |
| Every dispatcher migration and executable PostgreSQL contract remains present in both Python and Node provenance inventories | `node --test tests/dispatcher-inventory.test.mjs` (also included in `npm run validate`) |
| Bitemporal non-overlap, observably concurrent conflicting version insert, retroactive correction, and in-place rewrite rejection for versioned and other recorded-time HRIS facts | `bash tests/test_bitemporal_postgres.sh` against PostgreSQL 16 in Foundation CI |
| Cross-tenant composite-FK rejection, missing-context fail-closed RLS reads and writes, cross-context write rejection, and tenant-visible row isolation over every current HRIS table | `bash tests/test_tenant_isolation_postgres.sh` against PostgreSQL 16 in Foundation CI |
| Open-set caller-digest rejection, non-empty evidence enforcement, independently precomputed SHA-256 membership digest, membership/finalization race serialization, post-decision evidence-insert rejection, and evidence-set single-use enforcement | `bash tests/test_evidence_sealing_postgres.sh` against PostgreSQL 16 in Foundation CI |
| RFC 9562 Nil/Max sentinel rejection across every foundation UUID identity, including direct persistence paths | `bash tests/test_operational_uuid_postgres.sh` against PostgreSQL 16 in Foundation CI |
| Canonical audit-envelope digest verification, top-level PII allowlist, high-impact confirmation, atomic audit/outbox insertion, append-only audit mutation denial, legal/illegal lease transitions, terminal delivery immutability, and rollback on outbox failure | `bash tests/test_audit_outbox_postgres.sh` against PostgreSQL 16 in Foundation CI |
| Tenant-safe atomic outbox claiming and crash recovery: already-expired new-lease rejection, due-order claims, live-lease exclusion, pre-exhaustion takeover with incremented attempt/`lease_expired` evidence, active-tenant binding, opaque worker identity, and 1–3600 second future lease bounds | `bash tests/test_outbox_claim_postgres.sh` against PostgreSQL 16 in Foundation CI |
| Governed terminal outbox failure: no dispatcher-controlled attempt-budget signature, immutable stored budget (default 5), direct-terminal-DML rejection, exact recorded-owner enforcement, stored-budget exhaustion, retry-attempt-N+1 denial, exhausted expired-lease non-reclaimability, exact recorded-owner terminalization after final-lease expiry, terminal non-reclaimability, fabricated-nonterminal-escalation rejection, and append-only escalation evidence | `bash tests/test_outbox_dead_letter_postgres.sh` against PostgreSQL 16 in Foundation CI |
| Review-hardening and privileged recovery invariants for audit/outbox persistence | `bash tests/test_audit_outbox_hardening_postgres.sh` against PostgreSQL 16 in Foundation CI |
| Candidate-to-worker conversion identity, decision/evidence binding, tenant isolation and recorded-time integrity | `bash tests/test_candidate_worker_conversion_postgres.sh` against PostgreSQL 16 in Foundation CI |
| Predictive-validity study case worker/decision/evidence/criterion and recorded-time integrity | `bash tests/test_validity_study_case_postgres.sh` against PostgreSQL 16 in Foundation CI |
| Performance criterion observation Job, cycle, staffing, current-recorded-time, and UTC date-boundary integrity | `bash tests/test_criterion_observation_scope_postgres.sh` against PostgreSQL 16 in Foundation CI |
| Governed People mutation idempotency: tenant/route/key uniqueness, identical-command replay, changed-command rejection, rollback safety, append-only/TRUNCATE protection, forced RLS and concurrent exact-key serialization | `bash tests/test_people_mutation_idempotency_postgres.sh` against PostgreSQL 16 in Foundation CI |
| Tenant/actor/purpose authorization matrix and negative high-impact commands | service-specific unit and integration test commands recorded in each service package |
| AsyncAPI/CloudEvents envelope compatibility | provider and consumer contract test commands recorded beside the versioned event schema |
| External adapter timeout, malformed response, tenant mismatch, and unavailable-state handling | fake-server tests in each adapter package |
| Role-workspace keyboard, focus, exact-value, permission-denied, and confirmation states | Storybook interaction/a11y tests plus browser E2E for the owning workspace |

The PostgreSQL scripts apply the checked-in migration chain required by the contract under test to a fresh database. The bitemporal and evidence-sealing tests execute concurrency regressions with an observable database barrier instead of a fixed scheduling assumption. The tenant-isolation test proves both read and write enforcement with unprivileged `NOLOGIN NOBYPASSRLS` roles, so table-owner/superuser bypass cannot manufacture a passing tenant result. The evidence-sealing test compares database output with independently precomputed canonical SHA-256 fixtures and forces a membership transaction to hold the evidence-set row lock before finalization, proving the digest snapshot includes evidence that committed first. The audit/outbox contract stores exact `AuditOutboxEvent.canonical_json()` bytes, independently verifies their SHA-256 digest in PostgreSQL, rejects extra top-level PII fields even when a caller recomputes the digest, and exercises outbox lifecycle invariants separately from immutable audit facts. The outbox-claim contract proves an already-expired lease cannot be created, verifies deterministic tenant-scoped claims return the immutable event/digest while live leases are excluded, then lets a valid one-second lease expire and requires atomic takeover of that same row with attempt count 2, a new future lease, and explicit `lease_expired` evidence. The dead-letter contract applies migrations 0001 through 0007, proves the dispatcher cannot select its own terminal attempt budget, rejects direct terminal DML before matching immutable escalation evidence and the stored budget are satisfied, exercises the real retry/claim path through the database-owned default fifth attempt, rejects retry at attempt five, lets the final lease expire, proves a replacement worker cannot create attempt six, proves the row remains bound to the recorded worker identity, rejects a foreign finalizer, permits that exact recorded identity to append terminal evidence after expiry, and rejects fabricated escalation evidence for nonterminal work. The People mutation idempotency contract applies the authoritative migration chain through 0012, verifies the replay record is written in the same transaction as its authoritative fact and audit/outbox evidence, proves rollback leaves no false replay marker, and uses concurrent exact-key sessions to prove one canonical committed identity wins without duplicate business facts. Foundation CI executes every matrix entry independently; a cancelled, skipped, queued, absent, neutral, failed, stale, predecessor-head, status-only, or model-only matrix result is not database evidence for the current head.

Future service packages must publish their exact test, statement-coverage, branch-coverage, docstring, typecheck, and build commands in the package manifest and CI log.

## High-impact decision tests

Required negative and provenance tests include:

- an LLM or orchestration credential cannot create a selection-decision record;
- an LLM or integration adapter cannot transition `Candidate` to `Offered` or `Offered` to `Worker`;
- missing or insufficient Keyverse scope, actor, tenant, purpose, reason, confirmation, evidence reference, or evidence version fails closed;
- mutation authentication and tenant binding occur before request-body reads or identifier allocation, so unauthenticated input cannot consume parser or persistence work;
- a reused confirmation or idempotency key cannot bind to different command content;
- an identical tenant/route/idempotency-key retry replays the first committed created-record identity rather than issuing a duplicate authoritative write;
- concurrent exact-key requests serialize at the persistence boundary and cannot commit two different identities;
- previewed evidence versions must equal recorded evidence versions;
- an open evidence set rejects a caller-supplied digest, preventing a client assertion from masquerading as database-observed membership;
- finalizing a selection decision requires at least one versioned evidence member, computes the canonical SHA-256 digest in PostgreSQL, and seals exactly one evidence set in the same transaction;
- a membership write that acquired the evidence-set lock before finalization commits before the finalization snapshot is computed, and the resulting digest includes that member;
- a sealed evidence set rejects later membership changes and cannot be reused by another decision;
- a sealed evidence-set pointer must resolve back to the exact decision that consumed it;
- record, immutable audit evidence, pending outbox delivery, and any applicable idempotency binding either complete in one business transaction or leave no partial authoritative mutation;
- the database rejects digest-tampered audit bytes, non-allowlisted event fields, an event-id/tenant mismatch, and a high-impact event with no human confirmation reference;
- audit event rows reject update/delete and delivered or dead-lettered outbox rows reject later mutation;
- an outbox row cannot skip its lease state before delivery, a new lease must expire in the future, and an ordinary retry can return to pending only with cleared lease metadata, bounded failure classification, and remaining attempt budget;
- an outbox claim must match the active tenant context, use an opaque dispatcher identity and bounded duration, increment the attempt count exactly once per ownership grant, never reclaim a live lease, recover an expired lease only before exhaustion, and never create attempt N+1 after the durable maximum;
- dead-lettering must read an immutable database-owned `maximum_attempt_count` rather than accept a dispatcher budget, require the active tenant and exact recorded worker identity, require durable budget exhaustion plus matching immutable escalation evidence, reject structurally valid direct terminal DML before those invariants hold, reject foreign terminalization, and allow the recorded final-attempt identity to close an exhausted expired lease without adding an attempt;
- a cross-tenant foreign-key reference is rejected even when the referenced identifier exists in another tenant;
- an application role with missing tenant context sees no tenant-owned rows and cannot insert tenant-owned rows;
- a tenant-alpha application context cannot insert a tenant-beta row even when that beta tenant exists;
- a cross-tenant read or mutation is denied and its audit envelope cannot claim another tenant identity;
- a purpose header cannot enlarge a token's operation scope; and
- client errors contain an actionable `next_action` and random `support_reference` but no internal trace/span identifier, topology, tenant identifier, or PII.

## External psychometric contracts

Orgmetra does not combine fast-mlsirm and TEPP into one dependency. Production integration is admitted only from an immutable supported owner release. A raw repository revision may remain in provenance evidence but cannot satisfy the consumer contract by itself.

### fast-mlsirm

- Canonical repository: `ContextualWisdomLab/fast-mlsirm`.
- Historical reviewed source revision: `fb67ced09d8ee00542c05d56374537a9a7239751`; this is provenance only, not the production dependency identity.
- Current authority classification: `contract_projection_missing`. Immutable fast-mlsirm releases exist, but the previously documented `orgmetra.fast_mlsirm.v1` identifier is not an owner-published contract.
- Required production boundary: a domain-neutral released scientific-result/provenance contract consumed through an Orgmetra Anti-Corruption Layer. The owner contract, not fast-mlsirm, must remain free of Orgmetra-specific HR/tenant/decision fields.
- Owner: `workforce_validation`; the normal online path consumes a Psychometrics Commons immutable result snapshot rather than calling a kernel from a role workspace.
- Backend: Rust production arithmetic with bounded CPU multithreading and GPU parity for material kernels. Python/NumPy reference calculations cannot become production fallbacks.
- Required conformance coordinates: released package/contract version, supported public result/schema identity, exact owner locator and artifact/package digest, model/estimator/scoring configuration fingerprint, immutable input/evidence reference, backend/precision, uncertainty/diagnostics, convergence/failure semantics, reproducibility manifest or seed identity where applicable, and CPU/GPU parity evidence where promoted.
- Failure semantics: unknown/incompatible schema, nonconvergence, invalid input, unavailable capability, missing owner locator, and unsupported release all fail closed; no partial score publication or invented fallback estimate.

### TEPP

- Canonical repository: `ContextualWisdomLab/TEPP`.
- Historical reviewed source revision: `40adac9a26a8af85147ffa2795fb548ea243e0e5`; this is provenance only, not the production dependency identity.
- Current authority classification: `release_missing`; no immutable supported TEPP release is presently available to Orgmetra.
- Required production boundary: a released temporal-analysis owner contract with exact contract/version, artifact/package digest and owner locator.
- Owner: `workforce_validation`.
- Backend: Rust temporal/event/multilevel analysis services and immutable analytical artifacts.
- Required conformance coordinates: evidence references, event/effective/available times, knowledge cutoff, multiple-membership weights, model manifest, uncertainty, leakage audit, provenance digest and owner result locator.
- Failure semantics: invalid temporal order, insufficient evidence, nonconvergence, unavailable capability, missing/incompatible release and provenance mismatch fail closed; an analytical artifact is never promoted to HRIS truth.

### Psychometrics Commons snapshot linkage

- Canonical repository: `ContextualWisdomLab/psychometrics-commons`.
- Historical reviewed source revision: `cc5850a0d1eacbbf16d03075534fce460a8286e6`; this is provenance only, not the production dependency identity.
- Current authority classification: `release_missing`; no immutable supported Psychometrics Commons release is presently available to Orgmetra.
- Required production boundary: a released assessment execution/result-snapshot contract. Orgmetra stores purpose-minimized released owner references rather than copying foreign product persistence.
- A snapshot may be consumed only when the released owner contract/version, tenant, session, instrument/scoring coordinate, event prefix where applicable, digest, result identity and owner locator all agree.

Before production integration, each specialist contract requires:

- an immutable supported owner release and exact contract/schema version;
- artifact or package digest plus owner locator; a digest alone or bare repository SHA is insufficient;
- installed-package/API/schema compatibility tests rather than checkout/PYTHONPATH-only acceptance;
- fake-server or equivalent timeout, malformed result, unavailable, tenant/purpose mismatch and unknown-version tests at the owning adapter boundary;
- exact replay and provenance-link tests;
- fast-mlsirm Rust/reference and CPU/GPU parity evidence where the released result claims those paths;
- TEPP CPU/GPU parity for material kernels and leakage-safe temporal replay where applicable;
- negative tests proving `release_missing` and `contract_projection_missing` cannot fall back to a mutable branch, copied schema, floating `latest`, or unversioned result; and
- upgrade tests proving a new owner release cannot silently change the consumed result schema or scientific meaning.

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