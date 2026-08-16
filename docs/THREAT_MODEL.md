# Threat Model

## STRIDE summary

| Threat | Example | Preventive control | Detection evidence and required test |
|---|---|---|---|
| Spoofing | External identity treated as HR person identity | Separate `person_record` from the Keyverse subject; verify issuer, audience, tenant, actor binding, and token lifetime. | Authentication-denial audit; tests reject subject/person substitution and stale authorization. |
| Tampering | Selection evidence or audit envelope changed after decision | Append-only decision/evidence records; database-sealed evidence digest; append-only `audit_event_record`; database recomputation of SHA-256 over the exact canonical audit bytes; delivery state stored separately. | Integrity alert; tests reject update/delete, digest mismatch, added audit fields, illegal outbox state changes, and version mismatch. |
| Repudiation | Hiring manager denies a decision | Human confirmation reference, actor, tenant, purpose, reason, evidence versions, immutable audit event, and target-scoped delivery state. | Correlated decision/audit lookup; tests prove actor traceability and prohibit high-impact audit persistence without confirmation. |
| Information disclosure | PII broadcast or retained through an event bus | Opaque references, exact durable audit-field allowlist, field-level APIs, purpose-bound authorization, tenant-scoped encryption, and no copied mutable HR payload. | Payload scanner and database contract; tests reject extra employee-name/PII event fields even when their digest is recomputed. |
| Cross-tenant access | Tenant A reads, reconstructs, changes, or emits evidence for Tenant B HRIS facts by altering a path, header, reference, cache key, event, or by supplying a foreign fact with a colliding durable identifier to an in-memory decision. | Authenticated tenant context, resource tenant binding, explicit tenant scope in historical reconstruction and HRIS decision functions, audit event/tenant identity binding, forced RLS on audit/outbox relations, scoped authorization, service-owned database roles, tenant-aware cache keys, and consumer-side event validation. | `cross_tenant_access_denied` audit event with no sensitive values; integration/kernel/database tests attempt direct reads, writes, object-reference swaps, colliding identifiers, event tenant mismatch, cache poisoning, and replay across tenants and require denial or exclusion with unchanged target data. |
| Denial of service | Integration retries flood services | Idempotency, guarded outbox leasing, bounded exponential backoff and queue limits before production dispatcher release, circuit breaking, and per-tenant budgets. | Queue-depth/lease/retry telemetry; load and recovery tests must prove bounded work, expired-lease recovery, and fair tenant isolation before dispatcher release. |
| Elevation of privilege | LLM grants itself access or performs a high-impact transition | LLM outputs remain draft evidence; policy engine and human confirmation control writes; database revalidates high-impact confirmation in durable audit evidence. | Authorization-denial audit; tests reject LLM decision records, missing-confirmation audit events, and `Offered`/`Worker` transitions. |

## Model risk

LLM analysis may summarize, extract, or draft but cannot publish job profiles, approve selection, alter compensation, revise performance policy, or change employment state without a human decision record.

## Data risk

Blanket masking can break HR work. Orgmetra uses purpose-bound access, encryption, retention, audit, and export control so authorized users can work with required PII safely. Event and telemetry surfaces minimize PII even when the authoritative service is permitted to display it. `audit_event_record` keeps only the allowlisted governance envelope; delivery retries and leases live in `outbox_delivery_record` so mutable transport metadata cannot rewrite or expand retained audit evidence.
