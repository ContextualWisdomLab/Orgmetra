# ADR 0027: Govern candidate-initiated application withdrawal as immutable evidence

- **Status:** Proposed on active stacked PR; not protected-main truth until merged
- **Date:** 2026-08-21
- **Decision owner:** Orgmetra
- **Dependency:** ADR 0026 / PR #66 normalized candidate application

## Context

ADR 0026 intentionally keeps `withdrawn` out of raw application-stage persistence. A terminal value named `withdrawn` is not self-authenticating: if the persistence layer accepts the word from any staff-facing workflow, a staff caller can encode a shadow rejection that appears candidate-driven. A defensible HRIS therefore needs a distinct evidence boundary that binds one exact application, the initiating candidate identity assertion, versioned withdrawal evidence, time, tenant, and immutable audit/outbox correlation.

NIST SP 800-63-4 and SP 800-63B-4 provide current primary guidance for digital identity and authentication. Orgmetra does not claim NIST conformance or assign an assurance level in this slice; the relevant design principle is narrower: a candidate-shaped identifier is not itself proof that the authenticated claimant is that candidate. Authentication/identity-resolution evidence must be produced by the authorized identity adapter and carried into the governed operation as evidence.

The existing Orgmetra audit/outbox boundary uses CloudEvents-compatible envelopes. The CloudEvents project identifies v1.0.2 as the latest released core specification. PostgreSQL 16 row-level security and trigger semantics provide the local persistence mechanisms used here for tenant isolation and immutable validation. These sources inform the boundary but do not substitute for Orgmetra's product-specific controls.

## Decision

Migration `0015_candidate_withdrawal_governance.sql` introduces `candidate_withdrawal_record`, a tenant-owned append-only terminal fact separate from `candidate_application_stage_record`.

A withdrawal row binds:

1. one tenant-local `candidate_application_record`;
2. one `candidate:` initiating actor reference;
3. an `identity_resolution:` reference plus SHA-256 digest produced by the authorized identity/authentication boundary;
4. a `candidate_withdrawal_evidence:` reference plus SHA-256 digest and bounded positive evidence version;
5. the candidate-declared `withdrawn_at` instant;
6. one immutable tenant-local `audit_event_record`; and
7. the system `recorded_at` instant.

Exactly one withdrawal may exist for one application. The row is append-only: UPDATE, DELETE, and TRUNCATE are rejected. The table forces row-level security using Orgmetra's existing tenant-context function.

Before insert, `validate_candidate_withdrawal_evidence()` re-resolves the tenant-local application and immutable audit event. It rejects withdrawal before application submission and requires the audit envelope to bind the exact withdrawal record, candidate actor, purpose `candidate_withdrawal`, reason `candidate_requested`, withdrawal evidence reference, event time, and non-high-impact `application_withdrawn` result. A matching transactional outbox delivery record must already exist.

The generic audit API may represent many actor namespaces. Therefore `candidate_withdrawal_record` independently restricts its initiating actor to the `candidate:` namespace. A valid generic audit envelope with a `staff:` actor cannot become a withdrawal row.

## Identity boundary

This migration does **not** authenticate candidates by parsing the `candidate:` string and does not directly query Keyverse or any foreign application table. The `identity_resolution_reference` and digest are evidence inputs from Orgmetra's authorized identity adapter boundary. The adapter remains responsible for resolving the authenticated principal to the application candidate under the published identity contract before writing the withdrawal transaction.

The database then protects what it can authoritatively prove locally: tenant/application identity, candidate actor namespace, exact audit correlation, evidence shapes and versions, chronology, one-withdrawal cardinality, append-only history, outbox presence, and tenant RLS. This separation preserves standalone operation and the dedicated-writer boundary without pretending that database syntax alone establishes digital identity.

## Relationship to employment decisions

Candidate withdrawal is modeled as the candidate terminating their own application process, so the audit event is explicitly `high_impact=false` and carries no fabricated employer confirmation token. Employer-driven adverse or favorable outcomes remain governed by `selection_decision` and its human-confirmed evidence boundary. The raw application-stage vocabulary remains non-terminal; this migration does not re-add `withdrawn`, `rejected`, `closed`, or `hired` as ordinary stages.

If product requirements later allow an authorized representative to withdraw on a candidate's behalf, that is a separate delegation/representation contract with its own actor and authority evidence. It must not be implemented by broadening the current `candidate:` check to `staff:`.

## Consequences

- Candidate withdrawal is represented without overwriting candidate identity or smuggling a terminal outcome into an ordinary workflow stage.
- Staff callers cannot record a withdrawal merely by choosing a `withdrawn` status or by creating a generic audit envelope with a staff actor.
- Audit/event time and immutable evidence remain correlated with the exact withdrawal row.
- One application cannot accumulate contradictory multiple withdrawal facts.
- Missing tenant context fails closed under forced RLS; tenant Alpha and Beta withdrawals are mutually invisible to a `NOBYPASSRLS` reader.
- The boundary remains dependent on the application layer's authorized identity adapter for actual claimant authentication and identity resolution. This ADR does not claim otherwise.

## Rejected alternatives

### Re-add `withdrawn` to `candidate_application_stage_record`

Rejected because the stage row has no initiating-actor or identity-resolution provenance. That would recreate the shadow-rejection defect that ADR 0026 closed.

### Treat candidate withdrawal as `selection_decision`

Rejected because a candidate terminating their own application is not an employer selection decision. Reusing the high-impact employer-decision model would misstate authority and could manufacture an inappropriate human-confirmation requirement.

### Directly query Keyverse application tables from the database trigger

Rejected because it violates the dedicated-writer/service boundary and creates direct cross-service database coupling. Orgmetra consumes identity proof through its authorized adapter/API contract instead.

### Trust a `candidate:` string without evidence

Rejected because namespace syntax is correlation, not authentication. The governed row therefore requires explicit identity-resolution reference/digest evidence and exact audit binding in addition to the actor namespace.

## Evidence

- `tests/test_candidate_withdrawal_postgres.sh` proves the governed happy path, preserves fail-closed rejection of raw `withdrawn` stage persistence, and proves append-only history.
- `tests/test_candidate_withdrawal_security_postgres.sh` isolates one-withdrawal cardinality, valid-audit/staff-actor rejection, audit/evidence anti-forgery, positive Alpha/Beta RLS visibility, missing-context fail-closed behavior, and TRUNCATE rejection.
- `.github/workflows/candidate-withdrawal-quality.yml` checks out the exact candidate SHA, uses pinned PostgreSQL 16.14, runs both focused contracts, and requires a clean checkout afterward.
- Primary-source review and APA 7 references are recorded in `docs/doctoring/candidate-withdrawal-references.md`.
