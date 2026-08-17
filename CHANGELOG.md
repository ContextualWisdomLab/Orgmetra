# CHANGELOG

All notable changes to Orgmetra will be documented in this file.

## [Unreleased]

### Added

- Stacked governed audit/outbox slice via `AuditOutboxEvent`, `audit_event_record`, `outbox_delivery_record`, and `outbox_delivery_escalation_record`: CloudEvents 1.0-compatible PII-minimized metadata, exact canonical JSON bytes, database-verified SHA-256 digests, mandatory human confirmation for high-impact events, immutable audit evidence, tenant RLS, atomic audit/outbox insertion, guarded pending/leased/delivered/dead-lettered delivery state, tenant-safe `claim_outbox_delivery(...)` with deterministic due-work ordering, `FOR UPDATE ... SKIP LOCKED`, opaque worker identity, bounded future leases, immutable envelope return, and atomic takeover of genuinely expired leases only while retry attempts remain; owner-bound `complete_outbox_delivery(...)` and `retry_outbox_delivery(...)`; database-budget-governed `dead_letter_outbox_delivery(...)`; and a separately privileged `operator_dead_letter_expired_outbox_delivery(...)` recovery path for an exhausted final lease whose recorded worker identity is permanently unavailable. `maximum_attempt_count` is persisted on the delivery row, defaults to 5, is constrained to 1 through 100, and cannot be lowered by a dispatcher during finalization. Migration 0007 prevents retry or expired-lease takeover from creating attempt N+1; migration 0008 adds TRUNCATE guards, trusted function search paths, a due-work partial index, session-independent immutable envelope validation, and operator recovery that must append immutable escalation evidence before terminalization. Exponential/backoff policy selection, policy-specific producer configuration, and external delivery receipts remain subsequent work.
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
- PostgreSQL contract tests for bitemporal concurrency, tenant isolation, NOBYPASSRLS write isolation, decision-evidence sealing, immutable audit/outbox persistence, atomic dispatcher claiming, expired-lease crash recovery, owner-bound delivery completion/retry, stale-owner denial, database-owned retry-budget dead-letter escalation, attempt-N+1 denial after exhaustion, exhausted-final-lease non-reclaimability, recorded-owner terminalization after final-lease expiry, governed operator recovery for a lost final worker, direct-terminal-DML denial, TRUNCATE denial, trusted search-path enforcement, terminal non-reclaimability, fabricated nonterminal-escalation denial, append-only escalation evidence, and RFC 9562 Nil/Max sentinel rejection.
- Structural OpenAPI mutation tests that bind authorization scopes, command schemas, evidence limits, human confirmation, creation-location headers, and client-safe error contracts to their owning operations.
- Manifest digest, byte-count, and line-count validation with regressions preventing Python/Node foundation-artifact inventories and all executable PostgreSQL migration/contract provenance from drifting apart.
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
- Database guards for reversed or zero-length temporal intervals and append-only candidate-worker, selection-decision, decision-evidence, validation-study linkage, audit-event, and outbox-escalation records.
- Database-level rejection of cross-tenant references, post-decision evidence insertion, caller-supplied open-set evidence digests, empty decision evidence, sealed evidence-set reuse, digest-tampered audit envelopes, non-allowlisted audit payload fields, high-impact audit events without confirmation, illegal outbox state transitions, already-expired new dispatcher leases, live-lease theft, cross-tenant outbox claims, unsafe lease-owner identifiers, foreign-owner completion/retry/dead-letter, stale-owner completion after lease expiry, dispatcher-supplied terminal retry thresholds, retries and claims beyond `maximum_attempt_count`, direct premature dead-letter DML, fabricated escalation evidence for nonterminal delivery state, mutation of terminal escalation evidence, TRUNCATE of governed audit/outbox tables, caller-controlled SQL object shadowing, and RFC 9562 Nil/Max UUID sentinels across foundation and audit/outbox identities.
- Expired dispatcher ownership is recoverable only after the recorded lease deadline and while attempts remain; takeover preserves immutable event/audit identity and retry budget, increments the attempt count, issues a new future lease, and records `lease_expired` failure evidence. An expired final-attempt row is not reclaimable beyond the budget.
- Normal dead-lettering remains restricted to the exact recorded worker identity after the immutable database-owned retry budget is exhausted. If that final worker identity is permanently unavailable, a distinct operator-only function may terminalize only an already-expired exhausted lease, must supply an opaque operator reference and failure code, and must append matching immutable escalation evidence before the existing transition guard accepts the dead-letter state. The function is not executable by `PUBLIC`.
- Audit/outbox SQL boundaries pin a trusted `pg_catalog, public, pg_temp` search path while `PUBLIC` loses schema-creation privilege on `public`; immutable envelope validation uses C-collated deterministic comparisons and calendar-field validation rather than session-sensitive timestamp input parsing.
- Bitemporal reconstruction plus assignment, position-seat, and employment-exclusivity kernel decisions are tenant-scoped so foreign-tenant identifiers cannot leak historical facts, provide coverage, consume capacity, or create false conflicts.
- Keyverse outage policy that blocks PII and high-risk actions when current authorization cannot be verified.
- Cross-tenant threat, denial evidence, and negative authorization test contracts.
- Replaced client-visible internal trace identifiers with random support references and actionable next-step error guidance.

### Notes

- The protected default branch contains only the minimal bootstrap commit. The canonical foundation is PR #22; the governed audit/outbox persistence, dispatcher claim/crash-recovery, owner-bound completion/retry, database-owned retry-budget dead-letter escalation, lost-final-worker operator recovery, and review hardening slice is stacked on that exact head and is not protected-main truth until dependency order and fresh merge gates are satisfied.
