# Orgmetra migration adapter

This package creates **value-free, fail-closed migration handoff evidence** before a bounded HRIS import batch may be sent to an external ETL executor.

Use it when an operator has already inspected a source through the published MHTML ETL Gateway contract and has an approved mapping for one bounded Orgmetra HRIS batch. The package binds that evidence to an Orgmetra tenant, accountable actor, approval, purpose, mapping digest, source digest, target HRIS object families, and exact reviewed dependency revisions.

Trust-bearing primitive fields are fail-closed runtime evidence. The adapter accepts exact built-in strings for identifiers, references, codes, digests, dependency revisions, and fixed envelope states; exact built-in integers for bounded counts and sizes; and an exact tuple of exact string target codes. Caller-defined subclasses are rejected before reviewed equality, hashed allow-list membership, numeric bounds, or canonical JSON serialization can run, so custom Python comparison/hash methods cannot make accepted governance differ from the immutable evidence that is recorded.

It deliberately does **not**:

- parse MHTML or copy the MHTML ETL Gateway implementation;
- contain raw source headers, source values, names, email addresses, credentials, or connection strings;
- call mightyETL or any network endpoint;
- write directly to Orgmetra or another service's application tables;
- claim a migration completed merely because a handoff envelope was built.

## Example

```python
from orgmetra_migration_adapter import MigrationHandoffInput, build_migration_handoff

evidence = MigrationHandoffInput(
    tenant_record_id="10000000-0000-7000-8000-000000000001",
    migration_batch_reference="migration_batch:01JHRISMIGRATION01",
    actor_reference="keyverse_subject:01JHRISOPERATOR",
    approval_reference="approval:01JHUMANCONFIRM",
    purpose_code="hris_data_migration",
    reason_code="legacy_hris_cutover",
    human_confirmed=True,
    source_sha256="a" * 64,
    source_size_bytes=14220,
    schema_proposal_id="schema_proposal_" + "d" * 32,
    table_fingerprint_sha256="b" * 64,
    mapping_digest_sha256="c" * 64,
    record_count=2,
    target_object_codes=("person_record", "employment_record"),
)

handoff = build_migration_handoff(evidence)
print(handoff.digest_sha256())
print(handoff.next_action)
```

The adapter intentionally pins the exact reviewed MHTML ETL Gateway and mightyETL revisions. A dependency revision change fails closed until Orgmetra revalidates the published contract and updates the pin in a reviewed change.

`handoff.execution_mode == "bounded_atomic_batch"` is a **requested/contracted mode for the subsequent mightyETL execution boundary**. It is not an observed result and must never be treated as proof that any write occurred or that an executed migration completed atomically. Atomic completion requires separate execution-outcome evidence from the owner boundary plus reconciliation.

A successful handoff is **not** migration success. The next action is to submit the approved batch through the configured mightyETL integration boundary and reconcile the outcome before marking the migration complete.
