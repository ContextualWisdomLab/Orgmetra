"""Guard the exact immutable lookup key for base-weight owner evidence."""

from __future__ import annotations

from inspect import signature

from orgmetra_workforce_validation_api.base_weight_authority import (
    BaseWeightAuthorityReadPort,
)


def test_base_weight_read_port_requires_complete_reproducibility_tuple() -> None:
    """Require every caller-known coordinate needed to select one owner record."""
    parameters = set(signature(BaseWeightAuthorityReadPort.read_base_weight_authority).parameters)

    required_lookup_coordinates = {
        "tenant_record_id",
        "validity_study_id",
        "base_weight_evidence_receipt_reference",
        "base_weight_evidence_receipt_digest",
        "evidence_version",
        "source_universe_receipt_reference",
        "source_universe_receipt_version",
        "source_universe_receipt_digest",
        "sampling_design_receipt_reference",
        "sampling_design_receipt_version",
        "sampling_design_receipt_digest",
        "sampled_occurrence_set_digest",
        "selection_probability_set_digest",
        "selection_stage_count",
        "base_weight_method_code",
        "base_weight_method_version",
        "base_weight_artifact_digest",
        "constructed_at",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
    }
    assert required_lookup_coordinates <= parameters

    owner_resolved_chronology = {
        "source_universe_released_at",
        "sampling_design_released_at",
        "owner_contract_released_at",
        "released_at",
    }
    assert parameters.isdisjoint(owner_resolved_chronology)
