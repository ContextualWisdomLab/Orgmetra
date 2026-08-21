"""Adversarial runtime-type regressions for governed migration evidence."""

from __future__ import annotations

from dataclasses import replace

import pytest

from orgmetra_migration_adapter import (
    MAXIMUM_BATCH_RECORDS,
    MHTML_ETL_GATEWAY_REVISION,
    MIGHTY_ETL_REVISION,
    ContractViolation,
    MigrationHandoffInput,
    build_migration_handoff,
)


class ForgedEqualityText(str):
    """Carry unsafe text while pretending to equal one reviewed constant."""

    def __new__(cls, value: str, pretend: str) -> "ForgedEqualityText":
        """Create forged text with the reviewed value it should impersonate."""
        instance = super().__new__(cls, value)
        instance.pretend = pretend
        return instance

    def __eq__(self, other: object) -> bool:
        """Pretend to equal only the reviewed comparison value."""
        return other == self.pretend

    def __ne__(self, other: object) -> bool:
        """Invert the forged equality result for inequality guards."""
        return not self.__eq__(other)

    def __hash__(self) -> int:
        """Collide with the reviewed value for set-membership checks."""
        return hash(self.pretend)


class ForgedCount(int):
    """Carry an oversized count while defeating numeric bound comparisons."""

    def __le__(self, other: object) -> bool:
        """Pretend never to violate the positive lower bound."""
        return False

    def __gt__(self, other: object) -> bool:
        """Pretend never to exceed the reviewed batch upper bound."""
        return False


def _valid_input(**changes: object) -> MigrationHandoffInput:
    """Return one minimal approved migration handoff input for adversarial tests."""
    evidence = MigrationHandoffInput(
        tenant_record_id="10000000-0000-7000-8000-000000000001",
        migration_batch_reference="migration_batch:01JHRISMIGRATION01",
        actor_reference="keyverse_subject:01JHRISOPERATOR",
        approval_reference="approval:01JHUMANCONFIRM",
        purpose_code="hris_data_migration",
        reason_code="legacy_hris_cutover",
        human_confirmed=True,
        source_sha256="a" * 64,
        source_size_bytes=14_220,
        schema_proposal_id="schema_proposal_" + "d" * 32,
        table_fingerprint_sha256="b" * 64,
        mapping_digest_sha256="c" * 64,
        record_count=2,
        target_object_codes=("person_record", "employment_record"),
    )
    return replace(evidence, **changes)


def test_rejects_purpose_text_subclass_that_can_forge_reviewed_constant() -> None:
    """Unsafe underlying purpose text must not mint reviewed migration evidence."""
    forged = ForgedEqualityText("shadow_migration", "hris_data_migration")
    with pytest.raises(ContractViolation, match="purpose code is malformed"):
        build_migration_handoff(_valid_input(purpose_code=forged))


@pytest.mark.parametrize(
    ("field_name", "reviewed_value", "message"),
    [
        (
            "mhtml_contract_revision",
            MHTML_ETL_GATEWAY_REVISION,
            "MHTML ETL Gateway contract revision requires revalidation",
        ),
        (
            "mightyetl_contract_revision",
            MIGHTY_ETL_REVISION,
            "mightyETL contract revision requires revalidation",
        ),
    ],
)
def test_rejects_dependency_revision_subclasses_that_forge_pinned_equality(
    field_name: str,
    reviewed_value: str,
    message: str,
) -> None:
    """Dependency pins must be exact text, not caller-controlled equality objects."""
    forged = ForgedEqualityText("0" * 40, reviewed_value)
    with pytest.raises(ContractViolation, match=message):
        build_migration_handoff(_valid_input(**{field_name: forged}))


def test_rejects_target_code_subclass_that_forges_allow_list_membership() -> None:
    """A value-bearing target cannot impersonate an allowed HRIS object code."""
    forged = ForgedEqualityText("payroll_record", "person_record")
    with pytest.raises(ContractViolation, match="migration target object code is malformed"):
        build_migration_handoff(_valid_input(target_object_codes=(forged,)))


def test_rejects_integer_subclass_that_forges_batch_bounds() -> None:
    """Oversized record counts cannot override reviewed numeric comparisons."""
    forged = ForgedCount(MAXIMUM_BATCH_RECORDS + 500)
    with pytest.raises(ContractViolation, match="record count must be a positive integer"):
        build_migration_handoff(_valid_input(record_count=forged))


def test_rejects_envelope_mode_subclass_that_forges_fixed_privacy_state() -> None:
    """Canonical envelope privacy mode must be exact reviewed built-in text."""
    envelope = build_migration_handoff(_valid_input())
    forged = ForgedEqualityText("raw_values", "value_free")
    with pytest.raises(
        ContractViolation,
        match="migration envelope privacy mode must remain value_free",
    ):
        replace(envelope, privacy_mode=forged)
