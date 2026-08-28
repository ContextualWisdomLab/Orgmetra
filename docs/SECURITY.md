# Security

## Trust boundaries

- Orgmetra HRIS facts
- External CWL service references
- Document artifacts
- LLM draft outputs
- Assessment result snapshots
- PII fields
- Immutable audit evidence
- Mutable outbox delivery coordination
- Immutable outbox terminal-escalation evidence

## Security principles

- Purpose-bound authorization replaces indiscriminate masking.
- Sensitive data access is auditable, tenant-scoped, exact-target-correlated, field-scoped, and bounded by an operation-specific Keyverse scope.
- In-memory historical reconstruction and HRIS decision functions require explicit tenant scope; a caller-supplied collection containing colliding identifiers from another tenant cannot provide coverage, consume capacity, create false employment conflicts, or enter reconstructed history.
- Durable UUID identity columns reject the RFC 9562 Nil and Max sentinel values at the PostgreSQL boundary; reserved protocol sentinels cannot become tenant, person, employment, organization, job, position, assignment, candidate, decision, evidence, outcome, transition, audit-event, outbox-delivery, or outbox-escalation identities.
- LLM outputs cannot mutate authoritative facts without human-approved commands.
- External integrations use explicit adapters and fail closed.
- Event payloads carry opaque references, not broad PII broadcasts. Durable audit persistence enforces an exact top-level event-field allowlist so a caller cannot expand the retained audit payload with employee names, compensation, free-text evidence, or other mutable HR facts.
- Audit bytes are append-only and database digest-verified; asynchronous retry/lease/dead-letter state is normalized into a separate delivery relation, and terminal escalation evidence is normalized into its own append-only relation. Neither transport state nor escalation evidence can rewrite the audit fact.
- A dispatcher lease is an executable capability. Completion and retry require the exact owner of a still-live lease under the active tenant context. Before retry-budget exhaustion, expired ownership must be reclaimed through the guarded claim path; after exhaustion, claim/retry cannot create attempt N+1 and only the exact recorded stable worker reference may use the normal worker terminalization path. If that recorded final worker identity is permanently unavailable, a separately provisioned purpose-bound operator capability may terminalize only an already-expired exhausted lease through the audited recovery function; the operator role has no direct outbox read/write or escalation-insert privilege.
- Terminal dead-lettering additionally requires an immutable database-owned retry budget, durable exhaustion of that budget, a bounded failure classification, and matching opaque escalation evidence. A dispatcher cannot lower the threshold at finalization, structurally valid direct terminal DML cannot omit the evidence/budget invariant, a foreign worker cannot steal an exhausted row, a dead-lettered row cannot silently re-enter normal dispatch, and its escalation evidence cannot be updated or deleted.
- Privileged outbox recovery role names are fail-closed deployment identities. Migration 0008 rejects either reserved role name if it already exists instead of inheriting unknown memberships or ACLs; fresh NOLOGIN/NOBYPASSRLS roles are created only after that preflight. The temporary `CREATE` privilege needed for function ownership transfer is granted and revoked inside one transaction, so an interrupted handoff cannot strand schema-creation authority.
- Credentials and passkeys remain in Keyverse or external secret managers.
- Service database roles cannot query another service's application tables.
- Client error responses expose a random `support_reference`, never an internal trace/span identifier or encoded infrastructure context.

## Purpose-bound PII authorization

Orgmetra evaluates PII access before protected field values leave the authoritative HR boundary. Keyverse supplies authenticated identity and scope attributes through its published contract; Orgmetra owns the HR authorization policy and decision.

Every `PurposeBoundAccessRequest` must bind the active request tenant, authenticated actor tenant, target resource tenant, opaque actor reference, opaque target-resource reference, resource kind, purpose, operation, requested field names, and authenticated scope set. The target reference must identify the exact Orgmetra record with an opaque namespaced value suitable for audit correlation; it must not encode protected HR field values. The matching `PurposeBoundAccessPolicy` binds one tenant and immutable policy version to exactly one resource kind, purpose, operation, required Orgmetra scope, and permitted field set. There is no wildcard policy form.

Evaluation fails closed unless request, actor, resource, and policy tenants all agree; resource, purpose, and operation exactly match; the required operation-specific scope is present; and requested fields are a non-empty subset of permitted fields. UUID sentinels, malformed opaque actor or target references, wildcard-like codes, malformed scopes, empty sets, and mutable field/scope collections are rejected before evaluation. A valid purpose header cannot compensate for a missing scope or foreign resource tenant.

Authorization evidence contains only governance metadata, including the opaque actor and exact target-resource references, plus field names, never protected values. A denial returns a stable reason code and next safe action. An allow decision returns only the exact requested field subset, not every field the policy could permit. Both allow and denial evidence preserve the exact target reference so immutable audit correlation cannot collapse distinct person or employment records into one resource-kind-level event. These rules implement the Orgmetra side of the NIST SP 800-162 ABAC shape and attribute-integrity principles from NIST SP 800-205; ADR 0008 records the boundary.

## Mutation security contract

Every mutating HTTP operation and its server-side command handler requires one validated `Idempotency-Key` that crosses the command boundary into durable transactional replay state. The published OpenAPI employment, position, assignment, person, job-profile, and selection-decision command families require `X-Tenant-Reference`, `X-Actor-Reference`, and `X-Purpose-Code`; those values must match the authenticated Keyverse principal and the operation-specific least-privilege scope. The executable People mutation handlers added on this branch currently implement employment, position, and assignment creation with those headers. Person, job-profile, and selection-decision remain published foundation API contracts until their server handlers are integrated; their OpenAPI presence is not runtime evidence. Confirmed-hire materialization instead binds the tenant in `/v1/tenants/{tenant_record_id}/candidate-worker-conversions`, the business purpose in its exact query parameter, and the actor through the authenticated principal. It does not accept weaker duplicate actor/tenant/purpose header authorities.

All mutation families additionally require resource-scoped authorization and a versioned audit/provenance correlation reference. High-risk commands require an explicit human-confirmation boundary and immutable versioned evidence. Employment, position, and assignment commands carry confirmation/evidence on the command. Confirmed-hire materialization resolves the exact previously sealed `selection_decision` in the same tenant-bound transaction and rejects the mutation unless that decision records explicit human confirmation and sealed evidence provenance.

The Position lifecycle application boundary is a separate high-impact capability. It accepts only canonical, human-reviewed lifecycle evidence, re-resolves the locked tenant-qualified PositionVersion and current Assignment occupancy, rejects stale or forged snapshot digests and occupied closure/abolition, and records one immutable review/application/audit/outbox correlation. Its PostgreSQL function pins `search_path`, loses default `PUBLIC EXECUTE`, and uses forced RLS plus append-only and TRUNCATE guards; a review packet never authorizes the mutation by itself.

`people_mutation_idempotency_record` stores the tenant, route, idempotency key, semantic-command digest, committed resource identity, and transaction time in the same transaction as the authoritative HRIS fact and governed audit/outbox pair. A transaction-scoped advisory lock serializes concurrent requests for the exact tenant/route/key. A same-key same-command replay returns the first committed identity without repeating Person, Employment, candidate-worker conversion, audit, or outbox writes; a changed command under the same key fails closed. A rolled-back command leaves no successful replay marker. The idempotency relation is tenant-RLS isolated and append-only, including TRUNCATE protection.

A caller-controlled purpose value cannot substitute for a missing token scope. The OpenAPI contract is executable input to generated gateway and server validation; an implementation that accepts a request outside its published contract fails CI.

Internal traces remain in restricted telemetry. Customer-facing failures return a bounded `error_code`, actionable `message`, `next_action`, and random `support_reference`; the support lookup is access-controlled and retention-bound.

The same governance contract applies to selection decisions, compensation changes, terminations, promotions, job-profile publication, validation-study policy changes, data exports, and identity deprovisioning. Draft creation may use a narrower permission, but publication or authoritative state transition may not reuse draft-only authorization.

## High-risk action flow

1. **Review/Preview**: show target, consequences, actor, tenant, purpose, reason, and exact evidence versions.
2. **Confirm**: obtain an explicit, single-use confirmation reference from an authorized human.
3. **Record**: append the authoritative decision and evidence references under one idempotency key.
4. **Audit**: in the same business transaction, persist `AuditOutboxEvent.canonical_json()` plus its SHA-256 digest through `record_audit_outbox_event(...)`; PostgreSQL revalidates the allowlisted PII-minimized envelope, event/tenant binding, digest, and high-impact confirmation before a pending outbox row is created.
5. **Deliver**: asynchronous workers may mutate only guarded outbox delivery state. They may complete or retry only their exact live lease while budget remains. After the immutable database-owned attempt budget is durably exhausted, claim/retry cannot create another attempt; the exact recorded stable worker identity may append matching immutable escalation evidence and terminalize through the normal worker function. If that identity is permanently lost, only an explicitly provisioned `orgmetra_outbox_operator` capability may invoke the separate expired-lease recovery function; its fresh NOLOGIN/NOBYPASSRLS function owner performs narrowly granted transport DML, while the externally assignable operator role itself cannot select or update outbox rows or insert escalation rows directly. The deferred escalation-binding check is forced while SECURITY DEFINER privileges are still active and returned to deferred mode before control returns to the caller. Workers and operators cannot select a lower terminal threshold, fabricate nonterminal escalation evidence, reopen terminal rows, rewrite audit evidence, or infer a successful downstream receipt.

No LLM, integration adapter, or background worker may synthesize the human confirmation or transition a candidate to `Offered` or `Worker` autonomously.
