# CHANGELOG

All notable changes to Orgmetra will be documented in this file.

## [Unreleased]

### Added

- Stacked audit/outbox envelope contract via `AuditOutboxEvent`: CloudEvents 1.0-compatible metadata, tenant/actor/purpose/reason/evidence extensions, mandatory human confirmation for high-impact events, PII-minimized event data, and deterministic SHA-256 envelope digests at exact 100% new-module statement and branch coverage.
- `orgmetra_hris_kernel` 0.4.0 with exclusive-versus-concurrent employment, staffable position coverage, exclusive-seat capacity, and `validate_assignment_write` at 100% statement and branch coverage.
- `POST /v1/employment-records`, `POST /v1/position-records`, and `POST /v1/assignment-records` with the same Keyverse mutation context, confirmation, and versioned evidence composition as other high-impact commands.
- `employment_record_version.employment_concurrency_code` constrained to `exclusive` or `concurrent`.
- ADR 0005 for exclusive employment and staffable seats.
- `orgmetra_hris_kernel` 0.3.0 with identity-scoped bitemporal resolution, assignment-employment coverage, allocation-portfolio checks, and a Memorial Hospital RN correction case at 100% statement and branch coverage.
- `employment_record_version` and `position_record_version` so employment and position identity stay stable across retroactive corrections.
- `assignment_record.employment_record_id` bound to the same person as the covering employment.
- `orgmetra_keyverse_adapter` that binds an opaque Keyverse subject to a person and rejects passwords, passkeys, and tokens.
- Design tokens for the repeating HR actions: approve, review, correct, request evidence, compare, export, and escalate.
- ADR 0004 for employment/position versions and assignment-employment binding.
- Foundation product baseline for Orgmetra as an evidence-centered HRIS/HCM.
- CWL federated integration boundary map.
- Bitemporal HRIS data contract with stable identity anchors and versioned person-name facts.
- Durable organization/job anchors with normalized bitemporal organization hierarchy and job-definition version records.
- Core ERD, UML, PRD, TRD, user stories, storyboard, wireframes, Storybook inventory, security, test, and operability baseline.
- Effective-dated performance-cycle records linked to criterion observations.
- Versioned selection-decision evidence sets, normalized evidence membership, and validity-study links to exact decisions, evidence, and outcomes.
- PostgreSQL contract tests for bitemporal concurrency, tenant isolation, NOBYPASSRLS write isolation, and decision-evidence sealing.
- Structural OpenAPI mutation tests that bind authorization scopes, command schemas, evidence limits, human confirmation, creation-location headers, and client-safe error contracts to their owning operations.
- Manifest digest, byte-count, and line-count validation with a regression preventing Python and Node foundation-artifact inventories from drifting apart.
- Deterministic unfinished-work marker regressions that reject explicit TODO/TBD/FIXME markers while allowing ordinary explanatory prose.

### Changed

- Canonicalized service identifiers as two-or-more-word `snake_case` across architecture, deployment, ACL, metrics, and client contracts.
- Separated fast-mlsirm, TEPP, and Psychometrics Commons into immutable external scientific contracts.
- Defined 100% owned production statement and branch coverage as a CI gate where the pinned toolchain exposes those metrics.
- Made every baseline OpenAPI mutation declare its own least-privilege Keyverse scope while retaining finer purpose-bound authorization.
- Enforced non-empty half-open effective/system intervals in the database to match the domain contract.
- Bound every current HRIS fact to a tenant using tenant-qualified foreign keys and forced row-level security, including fail-closed missing-tenant-context read and write contracts.
- Made high-impact selection finalization require non-empty versioned evidence and compute the canonical SHA-256 evidence-set digest inside PostgreSQL before sealing the set to exactly one consuming decision.
- Serialized evidence-set membership writes and finalization on the evidence-set row before digest computation so concurrently committed evidence cannot be omitted from a sealed decision digest.
- Protected every current relation with recorded-system-time columns against in-place business mutation or deletion; corrections may only close an open recorded interval before a replacement fact is inserted.
- Tightened CI provenance by documenting the exact setup-node release and rejecting both tracked and untracked validation side effects.
- Pinned the PostgreSQL 16.14 CI service image to the reviewed Docker Official Image index digest and added a regression that rejects a mutable `postgres:16` service tag.
- Split employment and position identity from versioned status so corrections no longer mint a new employment or position identifier.
- Made assignment coverage status-aware: `active` and `leave` remain staffable while `terminated` and other non-eligible employment statuses fail closed.

### Security

- Purpose-bound PII access contract.
- LLM output constrained to draft evidence.
- No direct cross-service application-table access.
- Service-owned database schemas and roles inside the initially shared physical PostgreSQL cluster.
- Database guards for reversed or zero-length temporal intervals and append-only candidate-worker, selection-decision, decision-evidence, and validation-study linkage records.
- Database-level rejection of cross-tenant references, post-decision evidence insertion, caller-supplied open-set evidence digests, empty decision evidence, and sealed evidence-set reuse.
- Bitemporal reconstruction plus assignment, position-seat, and employment-exclusivity kernel decisions are tenant-scoped so foreign-tenant identifiers cannot leak historical facts, provide coverage, consume capacity, or create false conflicts.
- Keyverse outage policy that blocks PII and high-risk actions when current authorization cannot be verified.
- Cross-tenant threat, denial evidence, and negative authorization test contracts.
- Replaced client-visible internal trace identifiers with random support references and actionable next-step error guidance.

### Notes

- The protected default branch contains only the minimal bootstrap commit. The canonical foundation is PR #22; the audit/outbox envelope is stacked on that exact head and is not protected-main truth until both dependency order and fresh merge gates are satisfied.