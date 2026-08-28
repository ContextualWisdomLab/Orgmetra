# Candidate withdrawal traceability

## State

**Active stacked PR only.** This document describes `feat/governed-candidate-withdrawal` stacked on PR #66. It is not protected-`develop` truth until both dependency order and merge governance are satisfied.

## Requirement-to-evidence map

| Requirement | Implementation evidence | Executable evidence |
|---|---|---|
| Withdrawal belongs to one exact tenant-local application | composite FK `(tenant_record_id, candidate_application_record_id)` plus insert trigger re-resolution in `0015_candidate_withdrawal_governance.sql` | `test_candidate_withdrawal_postgres.sh`; `test_candidate_withdrawal_security_postgres.sh` |
| Candidate initiation cannot be replaced by a staff workflow action | `initiating_actor_reference` accepts only `candidate:` namespace; generic audit actor must exactly match the row | `test_candidate_withdrawal_security_postgres.sh` creates a fully valid generic staff-actor audit event and proves the withdrawal row rejects it |
| Identity syntax is not treated as authentication | row requires `identity_resolution_reference` and SHA-256 digest; authorized identity adapter remains responsible for claimant→candidate resolution | ADR 0027 documents the adapter boundary; database tests prove the evidence shape is mandatory but do **not** claim external identity authentication |
| Withdrawal evidence is versioned and immutable | withdrawal evidence reference/digest, bounded `evidence_version`, append-only UPDATE/DELETE/TRUNCATE guards | both candidate-withdrawal PostgreSQL tests |
| Audit envelope binds the exact withdrawal | insert trigger requires exact subject, actor, identity-resolution reference/digest, evidence reference/digest, evidence version, purpose, reason, event time and result; transactional outbox row required | `test_candidate_withdrawal_security_postgres.sh` supplies candidate-shaped but mismatched provenance and proves fail-closed rejection |
| Candidate withdrawal is not an employer high-impact decision | audit envelope requires `high_impact=false` and has no `orgmetraconfirmation`; employer outcomes remain in `selection_decision` | `test_candidate_withdrawal_postgres.sh`; migration trigger predicates |
| Raw ATS workflow cannot smuggle terminal withdrawal | PR #66 stage vocabulary remains non-terminal; PR #67 does not add `withdrawn` to it | `test_candidate_withdrawal_postgres.sh` attempts raw `withdrawn` stage insertion and requires `candidate_application_stage_code_check` |
| Application chronology is preserved | withdrawal cannot predate application `submitted_at`; audit time must equal `withdrawn_at` and not exceed `recorded_at` | migration trigger exercised by happy-path and anti-forgery contracts |
| One application has at most one withdrawal fact | unique `(tenant_record_id, candidate_application_record_id)` | security test uses a second otherwise-valid audit event so the duplicate fails specifically at `candidate_withdrawal_application_unique` |
| Tenant isolation fails closed | FORCE RLS with existing `current_tenant_record_id()` policy | security test uses a `NOBYPASSRLS` reader: no context sees zero; Alpha and Beta each see only their own row |
| Validation runs on exact candidate source | pinned checkout plus explicit `git rev-parse HEAD` equality proof | `.github/workflows/candidate-withdrawal-quality.yml` |

## Explicit non-claims

The database does not authenticate a human candidate, verify an external authenticator, or query Keyverse directly. `candidate:` is an opaque actor namespace, not proof of identity. The identity-resolution reference/digest is meaningful only when supplied by the authorized Orgmetra identity adapter after resolving the authenticated principal under the published identity contract. This slice deliberately preserves that service boundary.

The slice also does not implement candidate self-service UI, e-mail/SMS confirmation, delegated representative withdrawal, rescission/reinstatement, or employer closure. Those require separate governed commands and buyer-visible workflow design rather than broader status codes.

## Standards and research linkage

NIST SP 800-63-4 and SP 800-63B-4 inform the separation between an identifier and authenticated claimant evidence. CloudEvents v1.0.2 informs the existing event envelope shape. PostgreSQL 16 `CREATE POLICY` and `CREATE TRIGGER` semantics underpin the local tenant-isolation and insert/immutability enforcement mechanisms. APA 7 references and source notes are in `docs/doctoring/candidate-withdrawal-references.md`.
