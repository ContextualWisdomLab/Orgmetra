# Orgmetra Employment Leave Review

This package creates a **pre-mutation review packet** for employment leave and temporary employment-status transitions. It is not an eligibility engine, medical-certification store, payroll/benefits processor, legal conclusion, automated employment decision, or downstream execution client.

## What the packet binds

A packet correlates one authoritative Orgmetra tenant and proposed leave window to exact opaque canonical non-sentinel UUIDv4 references and SHA-256 evidence for:

- the authoritative Person and Employment record;
- the active Assignment/Job/Position scope snapshot that must be resolved at review time;
- the authoritative leave case and exact leave-policy version;
- work-continuity and benefits-continuity plans;
- a return-to-work plan;
- the exact personal-data handling-policy and retention-policy versions governing the PII-bearing packet; and
- separate requester and accountable reviewer references whose authoritative actor identities must still be resolved and proven distinct before approval.

`tenant_record_id` follows protected Orgmetra core's canonical non-sentinel operational-UUID contract, including valid UUIDv7 tenant identities. Packet-owned namespaced trust references remain canonical UUIDv4 so timestamp/node-derived correlation metadata cannot enter leaf-owned opaque references. The packet carries a bounded positive `evidence_version` in canonical evidence. Opaque Person, Employment, and leave-case references plus the requested leave dates are **minimum-necessary personal data**, not anonymous evidence. The packet therefore self-identifies `contains_person_pii=true`. Its exact handling and retention policy references/digests are immutable audit correlation evidence; the host must still enforce purpose-bound authorization, least privilege, retention/export controls, and audit.

## Privacy and human authority

The envelope deliberately excludes direct identifiers such as names/email addresses and does not copy medical or family information, substantive leave-reason narrative, compensation or benefit values, credentials, or free-form model output. `reason_code` is limited to non-sensitive workflow categories; the substantive leave reason remains in the authoritative, purpose-bound leave-case boundary.

`scope_verification_state` remains `requires_authoritative_resolution`, `mutation_state` remains `not_authorized_to_apply`, and `external_execution_state` remains `not_authorized_to_execute`. Direct construction and `dataclasses.replace(...)` cannot turn the packet into an approval or completed action, falsely relabel its worker/date correlation as PII-free, or remove/change the required privacy-policy evidence without changing canonical evidence and SHA-256.

Each live packet instance is also bound to the canonical evidence digest computed at construction time. `canonical_json()` snapshots the trust-bearing fields once, recomputes that digest, and fails closed if low-level mutation changed the issued evidence before export. An unsupported shallow-copied instance has no process-local issuance binding and therefore also fails closed. `dataclasses.replace(...)` deliberately creates a newly validated packet instance with its own issuance binding; this process-local defense is not a signature, durable uniqueness constraint, authorization token, or substitute for immutable audit/outbox persistence.

Immediately before approval, the host must re-resolve every packet reference inside the exact tenant context, prove requester/reviewer separation from resolved authoritative identities, prove the Person-to-Employment and active Assignment/Job/Position scope, then verify the leave case, leave-policy version, exact handling/retention policy versions, requested business dates, continuity plans, and return-to-work provenance. Any HRIS mutation must then go through the authoritative People boundary with its own authorization, idempotency, bitemporal persistence, and immutable audit/outbox evidence.

Canonical JSON and SHA-256 are correlation/integrity evidence only. UUID syntax does not prove tenant ownership, worker relationship, or policy validity. The packet does not prove leave eligibility, lawful use, policy applicability or enforcement, medical facts, approval, mutation, benefit correctness, or downstream execution.
