"""Executable contract for the governed migration handoff."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json

import pytest

from orgmetra_migration_adapter import (
    MAXIMUM_BATCH_RECORDS,
    MHTML_ETL_GATEWAY_REVISION,
    MIGHTY_ETL_REVISION,
    MIGRATION_CONTRACT_VERSION,
    ContractViolation,
    MigrationHandoffInput,
    build_migration_handoff,
)


SOURCE_DIGEST = "a" * 64
TABLE_DIGEST = "b" * 64
MAPPING_DIGEST = "c" * 64
TENANT_ID = "10000000-0000-7000-8000-000000000001"


def valid_input(**changes: object) -> MigrationHandoffInput:
    """Return one buyer-realistic, value-free approved migration batch."""
    evidence = MigrationHandoffInput(
        tenant_record_id=TENANT_ID,
        migration_batch_reference="migration_batch:01JHRISMIGRATION01",
        actor_reference="keyverse_subject:01JHRISOPERATOR",
        approval_reference="approval:01JHUMANCONFIRM",
        purpose_code="hris_data_migration",
        reason_code="legacy_hris_cutover",
        human_confirmed=True,
        source_sha256=SOURCE_DIGEST,
        source_size_bytes=14_220,
        schema_proposal_id="schema_proposal_" + "d" * 32,
        table_fingerprint_sha256=TABLE_DIGEST,
        mapping_digest_sha256=MAPPING_DIGEST,
        record_count=2,
        target_object_codes=("person_record", "employment_record"),
    )
    return replace(evidence, **changes)


def test_builds_deterministic_value_free_handoff() -> None:
    """The same approved evidence yields one PII-minimized canonical envelope."""
    evidence = valid_input(
        target_object_codes=("person_record", "employment_record"),
    )
    reversed_evidence = replace(
        evidence,
        target_object_codes=("employment_record", "person_record"),
    )

    first = build_migration_handoff(evidence)
    second = build_migration_handoff(reversed_evidence)

    assert first == second
    assert first.contract_version == MIGRATION_CONTRACT_VERSION
    assert first.target_object_codes == ("employment_record", "person_record")
    assert first.privacy_mode == "value_free"
    assert first.execution_mode == "bounded_atomic_batch"
    assert first.human_confirmed is True
    assert first.requires_reconciliation is True
    assert "reconcile" in first.next_action
    assert first.digest_sha256() == second.digest_sha256()
    assert len(first.digest_sha256()) == 64

    payload = json.loads(first.canonical_json())
    assert payload == first.to_dict()
    assert payload["mhtml_contract_revision"] == MHTML_ETL_GATEWAY_REVISION
    assert payload["mightyetl_contract_revision"] == MIGHTY_ETL_REVISION
    assert payload["record_count"] == 2
    serialized = first.canonical_json()
    for forbidden in (
        "display_name",
        "email",
        "source_header",
        "source_value",
        "password",
        "credential",
        "connection_string",
    ):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"tenant_record_id": "not-a-uuid"}, "tenant record identifier is malformed"),
        (
            {"tenant_record_id": "10000000000070008000000000000001"},
            "tenant record identifier must use canonical UUID text",
        ),
        (
            {"tenant_record_id": "{10000000-0000-7000-8000-000000000001}"},
            "tenant record identifier must use canonical UUID text",
        ),
        (
            {"tenant_record_id": "00000000-0000-0000-0000-000000000000"},
            "tenant record identifier uses a reserved UUID sentinel",
        ),
        (
            {"tenant_record_id": "ffffffff-ffff-ffff-ffff-ffffffffffff"},
            "tenant record identifier uses a reserved UUID sentinel",
        ),
        (
            {"migration_batch_reference": "migration batch 1"},
            "migration batch reference is malformed",
        ),
        ({"actor_reference": "actor with spaces"}, "actor reference is malformed"),
        ({"approval_reference": 7}, "approval reference is malformed"),
        ({"purpose_code": "HRIS Migration"}, "purpose code is malformed"),
        (
            {"purpose_code": "workforce_reporting"},
            "migration purpose must be hris_data_migration",
        ),
        ({"reason_code": "cutover reason"}, "reason code is malformed"),
        (
            {"human_confirmed": False},
            "migration handoff requires explicit human confirmation",
        ),
        (
            {"human_confirmed": 1},
            "migration handoff requires explicit human confirmation",
        ),
        ({"source_sha256": "A" * 64}, "source digest must be lowercase SHA-256"),
        ({"source_size_bytes": True}, "source size must be a positive integer"),
        ({"source_size_bytes": 0}, "source size must be a positive integer"),
        (
            {"schema_proposal_id": "schema_" + "d" * 32},
            "schema proposal identifier is malformed",
        ),
        (
            {"schema_proposal_id": None},
            "schema proposal identifier is malformed",
        ),
        (
            {"table_fingerprint_sha256": "short"},
            "table fingerprint must be lowercase SHA-256",
        ),
        (
            {"mapping_digest_sha256": None},
            "mapping digest must be lowercase SHA-256",
        ),
        ({"record_count": False}, "record count must be a positive integer"),
        ({"record_count": 0}, "record count must be a positive integer"),
        (
            {"record_count": MAXIMUM_BATCH_RECORDS + 1},
            "migration batch exceeds the reviewed record bound",
        ),
        (
            {"target_object_codes": []},
            "migration target objects must be a non-empty tuple",
        ),
        (
            {"target_object_codes": ()},
            "migration target objects must be a non-empty tuple",
        ),
        (
            {"target_object_codes": ("person_record", 7)},
            "migration target object code is malformed",
        ),
        (
            {"target_object_codes": ("person_record", "person_record")},
            "migration target objects must be unique",
        ),
        (
            {"target_object_codes": ("payroll_record",)},
            "migration target object is outside the HRIS core",
        ),
        (
            {"mhtml_contract_revision": "0" * 40},
            "MHTML ETL Gateway contract revision requires revalidation",
        ),
        (
            {"mightyetl_contract_revision": "0" * 40},
            "mightyETL contract revision requires revalidation",
        ),
    ],
)
def test_handoff_fails_closed_on_invalid_or_stale_evidence(
    changes: dict[str, object], message: str
) -> None:
    """Malformed governance or dependency drift never produces migration evidence."""
    with pytest.raises(ContractViolation, match=message):
        build_migration_handoff(valid_input(**changes))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        (
            {"contract_version": "orgmetra.migration_handoff.v0"},
            "migration envelope contract version is unsupported",
        ),
        (
            {"target_object_codes": ("person_record", "employment_record")},
            "migration target objects must be sorted and unique",
        ),
        (
            {"target_object_codes": ("person_record", "person_record")},
            "migration target objects must be unique",
        ),
        ({"tenant_record_id": "not-a-uuid"}, "tenant record identifier is malformed"),
        (
            {"tenant_record_id": "10000000000070008000000000000001"},
            "tenant record identifier must use canonical UUID text",
        ),
        (
            {"tenant_record_id": "{10000000-0000-7000-8000-000000000001}"},
            "tenant record identifier must use canonical UUID text",
        ),
        (
            {"migration_batch_reference": "migration batch 1"},
            "migration batch reference is malformed",
        ),
        ({"actor_reference": "actor with spaces"}, "actor reference is malformed"),
        ({"approval_reference": "approval with spaces"}, "approval reference is malformed"),
        ({"purpose_code": "workforce_reporting"}, "migration purpose must be hris_data_migration"),
        ({"reason_code": "cutover reason"}, "reason code is malformed"),
        ({"human_confirmed": False}, "migration handoff requires explicit human confirmation"),
        ({"human_confirmed": 1}, "migration handoff requires explicit human confirmation"),
        ({"source_sha256": "A" * 64}, "source digest must be lowercase SHA-256"),
        ({"source_size_bytes": 0}, "source size must be a positive integer"),
        (
            {"schema_proposal_id": "schema_" + "d" * 32},
            "schema proposal identifier is malformed",
        ),
        ({"table_fingerprint_sha256": "short"}, "table fingerprint must be lowercase SHA-256"),
        ({"mapping_digest_sha256": "short"}, "mapping digest must be lowercase SHA-256"),
        ({"record_count": 0}, "record count must be a positive integer"),
        (
            {"record_count": MAXIMUM_BATCH_RECORDS + 1},
            "migration batch exceeds the reviewed record bound",
        ),
        (
            {"target_object_codes": ("payroll_record",)},
            "migration target object is outside the HRIS core",
        ),
        (
            {"mhtml_contract_revision": "0" * 40},
            "MHTML ETL Gateway contract revision requires revalidation",
        ),
        (
            {"mightyetl_contract_revision": "0" * 40},
            "mightyETL contract revision requires revalidation",
        ),
        (
            {"privacy_mode": "raw_values"},
            "migration envelope privacy mode must remain value_free",
        ),
        (
            {"execution_mode": "best_effort"},
            "migration envelope execution mode is unsupported",
        ),
        (
            {"requires_reconciliation": False},
            "migration completion requires explicit reconciliation",
        ),
        (
            {"requires_reconciliation": 1},
            "migration completion requires explicit reconciliation",
        ),
        (
            {"next_action": ""},
            "migration envelope next action is noncanonical",
        ),
        (
            {"next_action": "Mark the migration complete."},
            "migration envelope next action is noncanonical",
        ),
    ],
)
def test_direct_envelope_construction_rejects_noncanonical_evidence(
    changes: dict[str, object], message: str
) -> None:
    """Public evidence cannot bypass canonical builder invariants."""
    envelope = build_migration_handoff(valid_input())
    with pytest.raises(ContractViolation, match=message):
        replace(envelope, **changes)


def test_evidence_objects_are_immutable() -> None:
    """Callers cannot rewrite governance evidence after validation."""
    evidence = valid_input()
    envelope = build_migration_handoff(evidence)

    with pytest.raises(FrozenInstanceError):
        evidence.record_count = 3  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        envelope.record_count = 3  # type: ignore[misc]


@pytest.mark.parametrize("bad_tenant", [None, 7])
def test_tenant_type_errors_use_safe_fixed_failure(bad_tenant: object) -> None:
    """Non-string tenant identifiers fail without reflecting attacker-controlled data."""
    with pytest.raises(
        ContractViolation, match="tenant record identifier is malformed"
    ) as exc_info:
        build_migration_handoff(valid_input(tenant_record_id=bad_tenant))
    assert str(bad_tenant) not in str(exc_info.value)


def test_all_supported_hris_targets_are_accepted_in_canonical_order() -> None:
    """The adapter accepts only the authoritative HRIS core object families."""
    envelope = build_migration_handoff(
        valid_input(
            target_object_codes=(
                "position_record",
                "assignment_record",
                "person_record",
                "organization_unit",
                "job_profile",
                "employment_record",
            )
        )
    )
    assert envelope.target_object_codes == (
        "assignment_record",
        "employment_record",
        "job_profile",
        "organization_unit",
        "person_record",
        "position_record",
    )
