# PostgreSQL restore rehearsal traceability

## Scope and truth status

Protected-main truth: `develop` currently requires encrypted PostgreSQL backups, point-in-time recovery, restore rehearsals, restored audit digest verification, preservation of outbox/audit evidence, and integrity checks before restored data is serviceable. This active PR adds executable recovery evidence; it does not change authoritative HRIS business semantics.

The rehearsal creates an isolated source database on one PostgreSQL service, applies the protected-main migration sequence, writes a tenant-bound bitemporal Person/Name fact plus immutable audit/outbox evidence, produces a real PostgreSQL custom-format dump, and restores it into a separate exact restored database on a second independent PostgreSQL service. That separation prevents a same-cluster rehearsal from silently inheriting cluster-global roles or other state from the source. The restored state, not the source state, is then validated.

PostgreSQL `pg_dump` is database-scoped and does not carry cluster-global roles. Before `pg_restore`, the clean target cluster explicitly recreates only the two least-privilege recovery principals required by migration 0008, then the database dump restores their object ownership and ACLs. The rehearsal verifies the restored owner/operator risk attributes, schema privileges, operator EXECUTE-only capability, bounded recovery-owner column privileges, escalation-table grants, and denial of direct operator transport-table DML. This models the operator prerequisite instead of relying on source-cluster residue; production deployments remain responsible for governing those cluster-global principals through their approved infrastructure/bootstrap path.

The executable lives under `.github/scripts` because it is an operational recovery rehearsal rather than a canonical migration/database-contract test. The core dispatcher provenance contract remains unchanged; `recovery-manifest.json` separately SHA-256-binds the recovery workflow, operational executable, executable contract and this traceability document so the recovery evidence has its own deterministic integrity boundary.

## Safe invocation boundary

The script is intentionally destructive only inside disposable rehearsal clusters: it drops the two cluster-global recovery principals while resetting its isolated source/restore services. It therefore refuses to proceed unless `RECOVERY_REHEARSAL_ALLOW_ROLE_DROP=1` is explicitly set. The checked-in workflow supplies that opt-in only to its two ephemeral PostgreSQL service containers; operators must not set it against a shared or production cluster.

Administrator connection URIs are parsed rather than edited by string suffix. The script accepts only `postgres`/`postgresql` schemes with a network location, rejects fragments, replaces only the database path with the isolated rehearsal database name, and preserves supported query parameters. Before restore, the produced custom-format dump must be non-empty and parse successfully through `pg_restore --list`.

## Executable evidence

| Requirement | Executable evidence | Expected result | Maturity |
|---|---|---|---|
| Real cross-cluster PostgreSQL backup/restore path | `.github/scripts/restore-rehearsal-postgres.sh` uses separate source/restore service containers plus `pg_dump --format=custom` and `pg_restore --exit-on-error` | Restore completes only on a distinct replacement PostgreSQL cluster | implemented_on_active_pr |
| Safe disposable-cluster invocation | The script requires `RECOVERY_REHEARSAL_ALLOW_ROLE_DROP=1`; executable tests prove missing opt-in and malformed administrator URIs fail before PostgreSQL connection | Cluster-global role cleanup cannot occur accidentally from the default invocation path | implemented_on_active_pr |
| Dump readability before restore | The dump must be non-empty and accepted by `pg_restore --list` | An empty or malformed archive cannot advance to restore | implemented_on_active_pr |
| Cluster-global recovery-principal prerequisite | Target bootstrap creates only `orgmetra_outbox_recovery_owner` and `orgmetra_outbox_operator` before restore | Database ownership/ACL restore succeeds without inheriting source-cluster roles | implemented_on_active_pr |
| Bitemporal business/system truth survives recovery | Restored `person_name_record` is resolved by exact name-record ID at explicit effective and known-at coordinates | Exactly one expected historical name is visible | implemented_on_active_pr |
| Audit tamper evidence survives recovery | SHA-256 is recomputed from restored `canonical_event_json` | Recomputed digest equals the restored envelope digest | implemented_on_active_pr |
| Audit/outbox lineage survives recovery | Restored outbox row joins the exact restored audit event | Exactly one pending delivery remains bound to the event | implemented_on_active_pr |
| Append-only protection survives recovery | UPDATE of the restored audit event is attempted | Database rejects mutation through the restored guard | implemented_on_active_pr |
| Bulk-history protection survives recovery | TRUNCATE of restored audit history is attempted | Database rejects TRUNCATE through the restored guard | implemented_on_active_pr |
| Least-privilege recovery boundary survives recovery | Restored function ownership/security-definer state, owner/operator risk attributes, schema privileges, operator EXECUTE grant, bounded owner update columns, escalation grants, and operator direct-DML denial are inspected | The function remains SECURITY DEFINER under the non-login owner; the operator retains EXECUTE-only capability with no direct transport-table DML; the owner retains only required read/escalation access and bounded transition-column updates | implemented_on_active_pr |
| Recovery evidence provenance | `recovery-manifest.json` records exact SHA-256, byte and line counts for the recovery workflow, executable, test and traceability | Exact candidate recovery evidence fails closed on drift | implemented_on_active_pr |
| Candidate checkout is the tested artifact | `.github/workflows/recovery-rehearsal-quality.yml` compares checkout HEAD with the event SHA | Test executes only on the exact candidate | implemented_on_active_pr |

## Operational interpretation

A GREEN rehearsal is recovery evidence for this migration state, PostgreSQL major image, and exact candidate SHA. It is not a substitute for production backup retention monitoring, point-in-time recovery drills across deployment-specific storage, encryption-key recovery, disaster-region exercises, downstream delivery receipt reconciliation, or tenant-specific legal retention controls. Those remain deployment/operator responsibilities unless separately automated.

The workflow pins the PostgreSQL 17.6 Alpine multi-platform image by its Docker Official Image index digest for both isolated services. It also preserves the existing immutable checkout action pin and does not write to any external CWL repository.

No certification claim is made. This evidence is designed to support acquisition diligence, business-continuity review, and SOC 2/CSAP evidence readiness without claiming certification or attestation.
