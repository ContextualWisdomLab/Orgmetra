# Orgmetra Employment Leave Review

This package creates a **pre-mutation review packet** for employment leave and temporary employment-status transitions. It is not an eligibility engine, medical-certification store, payroll/benefits processor, legal conclusion, automated employment decision, or downstream execution client.

## What the packet binds

A packet correlates one tenant and proposed leave window to exact opaque references and SHA-256 evidence for:

- the authoritative Person and Employment record;
- the active Assignment/Job/Position scope snapshot that must be resolved at review time;
- the authoritative leave case and exact leave-policy version;
- work-continuity and benefits-continuity plans;
- a return-to-work plan; and
- separate requester and accountable reviewer references whose authoritative actor identities must still be resolved and proven distinct before approval.

The packet carries a bounded positive `evidence_version` in canonical evidence. Opaque Person, Employment, and leave-case references plus the requested leave dates are **minimum-necessary personal data**, not anonymous evidence. The packet therefore self-identifies `contains_person_pii=true` and must remain behind the exact purpose-bound authorization, least-privilege, retention/export-control, and audit boundary.

## Privacy and human authority

The envelope deliberately excludes direct identifiers such as names/email addresses and does not copy medical or family information, substantive leave-reason narrative, compensation or benefit values, credentials, or free-form model output. `reason_code` is limited to non-sensitive workflow categories; the substantive leave reason remains in the authoritative, purpose-bound leave-case boundary.

`scope_verification_state` remains `requires_authoritative_resolution`, `mutation_state` remains `not_authorized_to_apply`, and `external_execution_state` remains `not_authorized_to_execute`. Direct construction and `dataclasses.replace(...)` cannot turn the packet into an approval or completed action or falsely relabel its worker/date correlation as PII-free.

Immediately before approval, the host must re-resolve every packet reference inside the exact tenant context, prove requester/reviewer separation from resolved authoritative identities, prove the Person-to-Employment and active Assignment/Job/Position scope, then verify the leave case, policy version, requested business dates, continuity plans, and return-to-work provenance. Any HRIS mutation must then go through the authoritative People boundary with its own authorization, idempotency, bitemporal persistence, and immutable audit/outbox evidence.

Canonical JSON and SHA-256 are correlation/integrity evidence only. They do not prove leave eligibility, lawful use, policy applicability, medical facts, approval, mutation, benefit correctness, or downstream execution.
