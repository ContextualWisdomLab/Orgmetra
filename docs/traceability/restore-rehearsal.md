# PostgreSQL restore rehearsal traceability

## Scope and truth status

Protected-main truth: `develop` currently requires encrypted PostgreSQL backups, point-in-time recovery, restore rehearsals, restored audit digest verification, preservation of outbox/audit evidence, and integrity checks before restored data is serviceable. This active PR adds executable recovery evidence; it does not change authoritative HRIS business semantics.

The rehearsal creates an isolated source database on one PostgreSQL service, applies the protected-main migration sequence, writes a tenant-bound bitemporal Person/Name fact plus immutable audit/outbox evidence, produces a real PostgreSQL custom-format dump, and restores it into a separate exact restored database on a second independent PostgreSQL service. That separation prevents a same-cluster rehearsal from silently inheriting cluster-global roles or other state from the source. The restored state, not the source state, is then validated.

PostgreSQL `pg_dump` is database-scoped and does not carry cluster-global roles. Before `pg_restore`, the clean target cluster explicitly recreates only the two least-privilege recovery principals required by migration 0008, then the database dump restores their object ownership and ACLs. This models the operator prerequisite instead of relying on source-cluster residue; production deployments remain responsible for governing those cluster-global principals through their approved infrastructure/bootstrap path.

The executable lives under `.github/scripts` because it is an operational recovery rehearsal rather than a canonical migration/database-contract test. The core dispatcher provenance contract remains unchanged; `recovery-manifest.json` separately SHA-256-binds the recovery workflow, operational executable, executable contract and this traceability document so the recovery evidence has its own deterministic integrity boundary.

## Executable evidence

| Requirement | Executable evidence | Expected result | Maturity |
|---|---|---|---|
| Real cross-cluster PostgreSQL backup/restore path | `.github/scripts/restore-rehearsal-postgres.sh` uses separate source/restore service containers plus `pg_dump --format=custom` and `pg_restore --exit-on-error` | Restore completes only on a distinct replacement PostgreSQL cluster | implemented_on_active_pr |
| Cluster-global recovery-principal prerequisite | Target bootstrap creates only `orgmetra_outbox_recovery_owner` and `orgmetra_outbox_operator` before restore | Database ownership/ACL restore succeeds without inheriting source-cluster roles | implemented_on_active_pr |
| Bitemporal business/system truth survives recovery | Restored `person_name_record` is resolved at explicit effective and known-at coordinates | Exactly one expected historical name is visible | implemented_on_active_pr |
| Audit tamper evidence survives recovery | SHA-256 is recomputed from restored `canonical_event_json` | Recomputed digest equals the restored envelope digest | implemented_on_active_pr |
| Audit/outbox lineage survives recovery | Restored outbox row joins the exact restored audit event | Exactly one pending delivery remains bound to the event | implemented_on_active_pr |
| Append-only protection survives recovery | UPDATE of the restored audit event is attempted | Database rejects mutation through the restored guard | implemented_on_active_pr |
| Bulk-history protection survives recovery | TRUNCATE of restored audit history is attempted | Database rejects TRUNCATE through the restored guard | implemented_on_active_pr |
| Privileged recovery boundary survives recovery | Restored recovery function ownership/security-definer state is inspected | Exactly one hardened recovery function remains owned by `orgmetra_outbox_recovery_owner` | implemented_on_active_pr |
| Recovery evidence provenance | `recovery-manifest.json` records exact SHA-256, byte and line counts for the recovery workflow, executable, test and traceability | Exact candidate recovery evidence fails closed on drift | implemented_on_active_pr |
| Candidate checkout is the tested artifact | `.github/workflows/recovery-rehearsal-quality.yml` compares checkout HEAD with the event SHA | Test executes only on the exact candidate | implemented_on_active_pr |

## Operational interpretation

A GREEN rehearsal is recovery evidence for this migration state, PostgreSQL major image, and exact candidate SHA. It is not a substitute for production backup retention monitoring, point-in-time recovery drills across deployment-specific storage, encryption-key recovery, disaster-region exercises, downstream delivery receipt reconciliation, or tenant-specific legal retention controls. Those remain deployment/operator responsibilities unless separately automated.

The workflow pins the PostgreSQL 17.6 Alpine multi-platform image by its Docker Official Image index digest for both isolated services. It also preserves the existing immutable checkout action pin and does not write to any external CWL repository.

No certification claim is made. This evidence is designed to support acquisition diligence, business-continuity review, and SOC 2/CSAP evidence readiness without claiming certification or attestation.
