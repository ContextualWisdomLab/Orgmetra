# Threat Model

## STRIDE summary

| Threat | Example | Mitigation |
|---|---|---|
| Spoofing | External identity treated as HR person identity | Separate `person_record` and Keyverse subject. |
| Tampering | Selection evidence changed after decision | Immutable evidence references and audit records. |
| Repudiation | Hiring manager denies decision | Actor, purpose, decision record, audit event. |
| Information disclosure | PII broadcast on event bus | Opaque references and field-level access APIs. |
| Denial of service | Integration retries flood services | Idempotency, backoff, queue limits. |
| Elevation of privilege | LLM grants itself access | LLM outputs remain draft evidence; policy engine controls writes. |

## Model risk

LLM analysis may summarize, extract, or draft but cannot publish job profiles, approve selection, alter compensation, or revise performance policy without human decision records.

## Data risk

Blanket masking can break HR work. Orgmetra uses purpose-bound access, encryption, retention, audit, and export control so authorized users can work with required PII safely.
