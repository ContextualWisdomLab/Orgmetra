# Orgmetra Foundation Implementation Plan

> Execute each task test-first on a reviewed branch. Keep commits bounded and the branch releasable after every completed task.

## Goal

Deliver an executable monorepo foundation and the first bitemporal HRIS vertical slice: person → employment → organization/job/position → assignment → retroactive correction → effective/known historical query → audit/outbox evidence.

## Task 1 — Workspace and quality gates

### Files

```text
package.json
pnpm-workspace.yaml
turbo.json
tsconfig.base.json
Cargo.toml
justfile
.editorconfig
.github/workflows/ci.yml
scripts/check-docstrings.mjs
scripts/check-service-boundaries.mjs
scripts/check-database-names.mjs
```

### TDD steps

1. Add failing repository-contract tests that require workspace files and scripts.
2. Add pnpm/Turborepo root with Node engine and deterministic package manager declaration.
3. Add TypeScript strict base config.
4. Add empty Cargo workspace for future Rust crates.
5. Add top-level commands: format, lint, typecheck, test, coverage, build, contracts, docs, security-local.
6. Add dependency-boundary and database-name checkers with focused tests.
7. Add CI using immutable action pins, install with frozen lockfile, and exact coverage/doc gates.
8. Run clean install and all repository checks.

## Task 2 — Shared contracts package

### Files

```text
packages/domain-contracts/
packages/event-contracts/
packages/authorization-contracts/
packages/provenance-contracts/
```

### TDD steps

1. Write failing tests for opaque IDs, tenant/purpose/correlation context, effective intervals, entity tags, Problem Details, and event envelope.
2. Implement dependency-free TypeScript value/schema contracts.
3. Add JSON Schema generation or committed schemas with drift tests.
4. Reject invalid UUIDs, time intervals, unknown required semantics, oversized strings/collections, and caller-controlled system time.
5. Reach 100% statement/branch coverage and public API docs.

## Task 3 — Core HRIS domain package

### Files

```text
services/core-hris-service/src/domain/
services/core-hris-service/tests/domain/
```

### TDD steps

1. RED: create person independent of identity-provider subject.
2. RED: create employment for person/legal entity.
3. RED: create organization, job version, position, and assignment.
4. RED: reject invalid/overlapping exclusive periods.
5. RED: allow concurrent assignments only under allocation policy.
6. RED: reject stale revision and invalid tenant/purpose context.
7. RED: retroactive correction retains prior recorded version.
8. Implement pure immutable domain rules and typed errors.
9. Add property tests for histories, overlaps, allocation, idempotency, and state transitions.
10. Reach exact coverage/doc gates.

## Task 4 — PostgreSQL schema and repositories

### Files

```text
database/core-hris/migrations/0001_foundation.sql
services/core-hris-service/src/persistence/
services/core-hris-service/tests/postgresql/
```

### TDD steps

1. Start an ephemeral supported PostgreSQL instance.
2. RED: clean migration and schema-name contract.
3. RED: foreign-key/tenant/non-overlap/version invariants.
4. Implement 3NF stable and version tables using multiword snake_case names.
5. Implement repositories with parameterized SQL and transaction boundaries.
6. RED/GREEN: concurrent assignment/correction races.
7. RED/GREEN: current, effective-at, known-at, and combined temporal queries.
8. RED/GREEN: transactional state + audit metadata + outbox.
9. Test upgrade/reapply/rollback-or-recovery and restore into an empty target.
10. Benchmark representative history/index queries.

## Task 5 — Authorization policy boundary

### Files

```text
services/core-hris-service/src/authorization/
packages/authorization-contracts/
services/core-hris-service/tests/authorization/
```

### TDD steps

1. RED: cross-tenant object/detail/history/search/export attempts.
2. RED: purpose header cannot self-authorize.
3. RED: field set differs for HR admin, manager, employee, auditor, and integration purpose.
4. Implement deterministic policy port and synthetic policy adapter.
5. Add step-up/approval requirements for linkage, correction, and export.
6. Ensure denial does not disclose hidden resource existence.
7. Scan logs/events/errors for PII and secrets.

## Task 6 — Audit and outbox

### Files

```text
services/core-hris-service/src/audit/
services/core-hris-service/src/events/
packages/event-contracts/
```

### TDD steps

1. RED: every accepted state change creates audit and outbox records atomically.
2. RED: rejected authorization/validation creates bounded security/audit evidence without state event.
3. Implement CloudEvents-compatible serialization with opaque references.
4. RED/GREEN: duplicate publication and consumer replay.
5. RED/GREEN: crash after commit/before publish and recovery.
6. Verify no clear PII in event/log fixtures.

## Task 7 — Core HRIS HTTP API

### Files

```text
services/core-hris-service/src/http/
schemas/openapi.yaml
services/core-hris-service/tests/http/
```

### TDD steps

1. RED API contract tests for create/get/correct/query endpoints.
2. Implement request bounds, auth context, idempotency, `If-Match`, pagination, temporal query, and Problem Details.
3. Generate/validate OpenAPI and examples.
4. Execute generated client smoke tests outside source tree.
5. Add malicious identifiers, Unicode, oversized input, hidden-resource, and provider-error tests.
6. Add `/health` liveness, `/ready` owned-dependency readiness, `/metrics` restricted surface.

## Task 8 — Gateway and Keyverse adapter contract

### Files

```text
apps/gateway/
integrations/cwl/keyverse-adapter/
```

### TDD steps

1. RED OIDC issuer/audience/signature/expiry/auth-context tests using synthetic keys.
2. RED confused-deputy tenant/purpose tests.
3. Implement gateway auth context and domain forwarding.
4. RED SCIM provisioning/deprovisioning intent, idempotency, timeout, and reconciliation.
5. Implement provider-neutral Keyverse port; no credential storage in HR records.
6. Verify Keyverse outage does not block already-authorized core HRIS reads/writes except dependent provisioning actions.

## Task 9 — Storybook foundations and HR temporal UI

### Files

```text
packages/ui-components/
apps/hr-workspace/
```

### TDD steps

1. Implement Storybook test harness and accessibility/visual/interaction gates.
2. Build foundational fields, states, purpose banner, temporal range, Bitemporal Lens, timeline, assignment split, error/degraded/permission components.
3. Build HR Home and Employee Profile page stories from synthetic contracts.
4. Implement browser flow for create employment/position/assignments and historical correction.
5. Verify keyboard, focus, screen-reader state, 200% zoom, mobile approval/correction, and exact-value alternatives.
6. Match selected Figma baseline and run visual QA.

## Task 10 — Deployment and release evidence

### Files

```text
compose.yaml
infrastructure/kubernetes/
docs/operations/
.github/workflows/release.yml
```

### TDD steps

1. Add local Compose with PostgreSQL and core/gateway/workspace.
2. Add non-root/read-only/restricted container contract tests.
3. Add provider-neutral Kubernetes reference with default-deny network policy, probes, resources, disruption/rollout settings, and digest placeholders.
4. Add backup/restore scripts and real CI rehearsal.
5. Add migration/deploy dry-run and rollback/recovery runbook.
6. Generate SBOM, provenance, signatures/hashes, and reproducible package evidence.
7. Update changelog/version only after exact integrated protected-head acceptance.

## Cross-task acceptance

- No direct cross-service SQL or service-internal imports.
- 3NF and database naming checks pass.
- Bitemporal and authorization invariants hold under concurrency.
- Clear PII is available only through authorized purpose-bound views.
- Events/logs/traces/model paths contain no unnecessary PII or secrets.
- All customer-facing errors identify the next safe action.
- 100% production statement/branch coverage and public API docs.
- Canonical docs, ADRs, UML, ERD, OpenAPI/events, and traceability match code.
