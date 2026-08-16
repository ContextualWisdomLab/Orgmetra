# Security

## Trust boundaries

- Orgmetra HRIS facts
- External CWL service references
- Document artifacts
- LLM draft outputs
- Assessment result snapshots
- PII fields
- Audit/provenance records

## Security principles

- Purpose-bound authorization replaces indiscriminate masking.
- Sensitive data access is auditable, tenant-scoped, field-scoped, and bounded by an operation-specific Keyverse scope.
- In-memory historical reconstruction and HRIS decision functions require explicit tenant scope; a caller-supplied collection containing colliding identifiers from another tenant cannot provide coverage, consume capacity, create false employment conflicts, or enter reconstructed history.
- Durable UUID identity columns reject the RFC 9562 Nil and Max sentinel values at the PostgreSQL boundary; reserved protocol sentinels cannot become tenant, person, employment, organization, job, position, assignment, candidate, decision, evidence, outcome, or transition identities.
- LLM outputs cannot mutate authoritative facts without human-approved commands.
- External integrations use explicit adapters and fail closed.
- Event payloads carry opaque references, not broad PII broadcasts.
- Credentials and passkeys remain in Keyverse or external secret managers.
- Service database roles cannot query another service's application tables.
- Client error responses expose a random `support_reference`, never an internal trace/span identifier or encoded infrastructure context.

## Mutation security contract

Every mutating HTTP operation and its server-side command handler must require and validate:

- `Idempotency-Key`;
- `X-Tenant-Reference`;
- `X-Actor-Reference`;
- `X-Purpose-Code`;
- an authenticated Keyverse principal bound to the actor and tenant;
- the operation-specific least-privilege Keyverse scope declared in OpenAPI;
- resource-scoped authorization; and
- a versioned audit/provenance correlation reference.

High-risk commands additionally require a non-empty decision reason, explicit confirmation reference, and at least one immutable evidence reference with a version. A caller-controlled purpose header cannot substitute for a missing token scope. The OpenAPI contract is executable input to generated gateway and server validation; an implementation that accepts a request outside that contract fails CI.

Internal traces remain in restricted telemetry. Customer-facing failures return a bounded `error_code`, actionable `message`, `next_action`, and random `support_reference`; the support lookup is access-controlled and retention-bound.

The same contract applies to selection decisions, compensation changes, terminations, promotions, job-profile publication, validation-study policy changes, data exports, and identity deprovisioning. Draft creation may use a narrower permission, but publication or authoritative state transition may not reuse draft-only authorization.

## High-risk action flow

1. **Review/Preview**: show target, consequences, actor, tenant, purpose, reason, and exact evidence versions.
2. **Confirm**: obtain an explicit, single-use confirmation reference from an authorized human.
3. **Record**: append the authoritative decision and evidence references under one idempotency key.
4. **Audit**: append actor and policy context before emitting the external event.

No LLM, integration adapter, or background worker may synthesize the human confirmation or transition a candidate to `Offered` or `Worker` autonomously.
