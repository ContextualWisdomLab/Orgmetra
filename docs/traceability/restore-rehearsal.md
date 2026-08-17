# PostgreSQL restore rehearsal traceability

## Scope and truth status

Protected-main truth: `develop` currently requires encrypted PostgreSQL backups, point-in-time recovery, restore rehearsals, restored audit digest verification, preservation of outbox/audit evidence, and integrity checks before restored data is serviceable. This active PR adds executable recovery evidence; it does not change authoritative HRIS business semantics.

The rehearsal creates an isolated source database, applies the protected-main migration sequence, writes a tenant-bound bitemporal Person/Name fact plus immutable audit/outbox evidence, produces a real PostgreSQL custom-format dump, restores it into a separate exact restored database, and validates the restored state rather than the source state.

## Executable evidence

| Requirement | Executable evidence | Expected result | Maturity |
|---|---|---|---|
| Real PostgreSQL backup/restore path | `tests/test_restore_rehearsal_postgres.sh` uses `pg_dump --format=custom` and `pg_restore --exit-on-error` | Restore completes into an independently created database | implemented_on_active_pr |
| Bitemporal business/system truth survives recovery | Restored `person_name_record` is resolved at explicit effective and known-at coordinates | Exactly one expected historical name is visible | implemented_on_active_pr |
| Audit tamper evidence survives recovery | SHA-256 is recomputed from restored `canonical_event_json` | Recomputed digest equals the restored envelope digest | implemented_on_active_pr |
| Audit/outbox lineage survives recovery | Restored outbox row joins the exact restored audit event | Exactly one pending delivery remains bound to the event | implemented_on_active_pr |
| Append-only protection survives recovery | UPDATE of the restored audit event is attempted | Database rejects mutation through the restored guard | implemented_on_active_pr |
| Bulk-history protection survives recovery | TRUNCATE of restored audit history is attempted | Database rejects TRUNCATE through the restored guard | implemented_on_active_pr |
| Privileged recovery boundary survives recovery | Restored recovery function ownership/security-definer state is inspected | Exactly one hardened recovery function remains owned by `orgmetra_outbox_recovery_owner` | implemented_on_active_pr |
| Candidate checkout is the tested artifact | `.github/workflows/recovery-rehearsal-quality.yml` compares checkout HEAD with the event SHA | Test executes only on the exact candidate | implemented_on_active_pr |

## Operational interpretation

A GREEN rehearsal is recovery evidence for this migration state, PostgreSQL major image, and exact candidate SHA. It is not a substitute for production backup retention monitoring, point-in-time recovery drills across deployment-specific storage, encryption-key recovery, disaster-region exercises, downstream delivery receipt reconciliation, or tenant-specific legal retention controls. Those remain deployment/operator responsibilities unless separately automated.

The workflow pins the PostgreSQL 17.6 Alpine multi-platform image by its Docker Official Image index digest. It also preserves the existing immutable checkout action pin and does not write to any external CWL repository.

No certification claim is made. This evidence is designed to support acquisition diligence, business-continuity review, and SOC 2/CSAP evidence readiness without claiming certification or attestation.
