# ADR 0114 — Persist reason-free Employment absence truth bitemporally

- Status: Proposed — active PR only
- Owner: Orgmetra HRIS core
- Parent dependency: PR #113 (`feat/employment-absence-truth`)
- Default-branch truth at decision time: `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` does not contain this persistence relation.

## Context

PR #113 defines a value-minimized, reason-free Employment absence fact in the HRIS kernel. Commercial HRIS operation also needs durable reconstruction by business-effective time and system-recorded time without turning leave reasons, medical/family information, benefit details, discipline, free-form case notes, compensation, ratings, or model output into generic core fields.

A persistence boundary must preserve tenant and Employment/Person scope, correction-not-rewrite history, and one operational confirmed absence truth per Employment coordinate. It must also remain descriptive: an absence fact is not authority for attendance discipline, termination, compensation, benefits, or any other high-impact employment decision.

## Decision

Add two 3NF relations:

1. `employment_absence_record` is the stable tenant-qualified absence identity and binds exactly one existing same-tenant Employment/Person pair.
2. `employment_absence_version` holds status (`confirmed` or `cancelled`), effective interval, system-recorded interval, evidence correlations, and fixed non-decision governance state.

The version relation uses PostgreSQL-owned `transaction_timestamp()` for system time. An open version can only be corrected by closing `recorded_to` at the current transaction timestamp; all other UPDATE/DELETE/TRUNCATE attempts fail closed. A new version then records the corrected fact without rewriting history.

Before insert, the database requires current system-visible `active` or `leave` Employment versions to cover the entire proposed absence effective interval. A tenant-qualified transaction-scoped advisory lock serializes absence mutations for one Employment, after which the insert rejects a second overlapping `confirmed` absence identity. Lock-key collisions only reduce concurrency; they do not relax the invariant.

Both relations use ENABLE + FORCE ROW LEVEL SECURITY with transaction-local tenant context. The migration stores opaque audit/outbox references and SHA-256 evidence correlations but does not query another service's application tables.

## Privacy and decision boundary

No generic reason, diagnosis, family detail, statutory category, disciplinary note, benefit value, free-form note, compensation value, rating, or LLM output is stored. Sensitive leave-case material requires a separate purpose-bound case owner.

`decision_authority_state` is fixed to `not_authorized_for_employment_decision`. Downstream high-impact use must re-authorize purpose and actor, re-resolve fresh Employment/absence truth, record human review/reason/evidence version, and emit immutable audit evidence through the authoritative owner boundary.

## Consequences

- Buyers can reconstruct operational absence truth as-of business and system time after the parent contract is integrated.
- Correction preserves what the system previously knew instead of rewriting the past.
- Concurrent overlapping confirmed absences fail closed rather than being silently consolidated.
- An Employment must have active/leave coverage for the entire persisted absence interval.
- This PR remains stacked and Draft until #113 integrates; parent checks/reviews are not transferable.
- After parent integration, this lane must retarget to fresh `develop`, reconcile migration numbering, and rerun all applicable CI/security/recovery/product gates on the resulting exact head.
