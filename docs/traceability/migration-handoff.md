# Governed migration handoff traceability

## Status

Protected `develop` currently contains the governed migration-handoff boundary. PR #71 hardens only Orgmetra-owned runtime evidence integrity on top of that protected truth; it does not mutate MHTML ETL Gateway, mightyETL, or any other dedicated-writer dependency.

| Requirement | Decision / owner contract | Production implementation | Executable evidence |
|---|---|---|---|
| Bind the immutable source without copying source values | MHTML ETL Gateway revision `779254927abb1e7cee80fd949907ccd03f9fc7be`; ADR 0012 | `MigrationHandoffInput.source_sha256`, `source_size_bytes`, value-free proposal identity/fingerprint | deterministic handoff and malformed-digest regressions |
| Preserve accountable migration governance | ADR 0012 | tenant UUID, migration-batch reference, actor, approval, `hris_data_migration` purpose, reason, strict human confirmation | malformed context, non-boolean confirmation, and hostile runtime-subclass regressions |
| Prevent runtime objects from forging reviewed evidence | Python data-model semantics; PR #71 | exact built-in `str`, `int`, and `tuple` primitives at trust-bearing validation/equality/hash/comparison boundaries | `test_runtime_evidence_integrity.py` purpose, dependency-revision, target allow-list, batch-bound, and envelope-mode adversarial regressions |
| Revalidate foreign contract drift rather than silently adapting | ADR 0012; exact owner revisions | `MHTML_ETL_GATEWAY_REVISION`, `MIGHTY_ETL_REVISION`, each requiring exact built-in text before equality | stale-revision plus hostile revision-subclass regressions |
| Keep the handoff bounded | mightyETL reviewed bounded-atomic-batch contract; ADR 0012 | `MAXIMUM_BATCH_RECORDS = 1000`; exact built-in positive integer record count | zero/bool/over-bound plus hostile integer-subclass regression |
| Restrict import targets to authoritative HRIS core | Orgmetra core model; ADR 0001; ADR 0012 | exact built-in tuple and string elements followed by allow-list validation for `person_record`, `employment_record`, `organization_unit`, `job_profile`, `position_record`, `assignment_record` | all-core-family success plus unsupported/duplicate/hostile-subclass target rejection |
| Prevent raw-value/credential shadow stores | MHTML value-free contract; ADR 0012 | package input/output has no raw header, source value, credential, connection or SQL field | serialized-envelope non-disclosure regression and public API review |
| Make pre-write evidence reproducible | W3C PROV-DM design traceability; ADR 0012 | sorted target codes, canonical JSON, SHA-256 digest | reversed-order equivalence plus exact `hashlib.sha256(canonical_json)` assertion |
| Keep requested execution semantics separate from observed outcomes | mightyETL owner contract; ADR 0012 | exact built-in `execution_mode="bounded_atomic_batch"` records only the requested/contracted subsequent execution mode; it is not proof of writes, completion, or observed atomicity | direct-constructor canonical-mode and hostile-subclass rejection plus documentation contract |
| Do not confuse handoff with migration completion | ADR 0012 | `requires_reconciliation=True` plus exact built-in actionable `next_action` | direct-constructor bypass rejection and deterministic handoff regression |
| Preserve dedicated-writer ownership | ADR 0002; ADR 0012 | no MHTML/mightyETL source mutation, no network call, no cross-service SQL | package dependency surface and code review |
| Keep owned behavior fully covered | Orgmetra quality policy | exact-head migration quality workflow | 100% statement and branch coverage gate |

A consumer MUST obtain separate execution-outcome evidence from the configured owner boundary and reconcile it before asserting migration completion or atomic execution. The pre-write envelope alone is never completion evidence. PR #71 changes only the local validation trust boundary: Python user-defined subclasses can override rich comparison and hashing behavior, so trust-bearing primitives are normalized by rejection to exact built-in runtime types before reviewed equality, membership, bounds, or canonical serialization are evaluated.
