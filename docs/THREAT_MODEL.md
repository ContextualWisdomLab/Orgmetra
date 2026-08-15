# Threat Model

## STRIDE summary

| Threat | Example | Preventive control | Detection evidence and required test |
|---|---|---|---|
| Spoofing | External identity treated as HR person identity | Separate `person_record` from the Keyverse subject; verify issuer, audience, tenant, actor binding, and token lifetime. | Authentication-denial audit; tests reject subject/person substitution and stale authorization. |
| Tampering | Selection evidence changed after decision | Append-only decision and evidence records; versioned evidence digest; idempotent command binding. | Integrity alert; tests reject update/delete and version mismatch. |
| Repudiation | Hiring manager denies a decision | Human confirmation reference, actor, tenant, purpose, reason, evidence versions, and immutable audit event. | Correlated decision/audit lookup; tests prove actor traceability for asynchronous consumers. |
| Information disclosure | PII broadcast on an event bus | Opaque references, field-level APIs, purpose-bound authorization, and tenant-scoped encryption. | Payload scanner and access log; tests reject broad PII event fields. |
| Cross-tenant access | Tenant A reads or changes Tenant B HRIS facts by altering a path, header, reference, cache key, or event. | Authenticated tenant context, resource tenant binding, scoped authorization, service-owned database roles, tenant-aware cache keys, and consumer-side event validation. | `cross_tenant_access_denied` audit event with no sensitive values; integration tests attempt direct reads, list leakage, writes, idempotency-key reuse, object-reference swaps, cache poisoning, and event replay across tenants and require denial with unchanged target data. |
| Denial of service | Integration retries flood services | Idempotency, bounded exponential backoff, queue limits, circuit breaking, and per-tenant budgets. | Queue-depth and retry telemetry; load tests prove bounded work and fair tenant isolation. |
| Elevation of privilege | LLM grants itself access or performs a high-impact transition | LLM outputs remain draft evidence; policy engine and human confirmation control writes. | Authorization-denial audit; tests reject LLM decision records and `Offered`/`Worker` transitions. |

## Model risk

LLM analysis may summarize, extract, or draft but cannot publish job profiles, approve selection, alter compensation, revise performance policy, or change employment state without a human decision record.

## Data risk

Blanket masking can break HR work. Orgmetra uses purpose-bound access, encryption, retention, audit, and export control so authorized users can work with required PII safely. Event and telemetry surfaces minimize PII even when the authoritative service is permitted to display it.
