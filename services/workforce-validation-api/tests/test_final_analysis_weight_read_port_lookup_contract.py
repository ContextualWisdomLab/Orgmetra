"""Guard the exact immutable lookup key for final analysis-weight owner evidence."""

from __future__ import annotations

from inspect import signature

from orgmetra_workforce_validation_api.final_weight_authority import (
    FinalAnalysisWeightAuthorityReadPort,
)


def test_final_analysis_weight_read_port_requires_complete_reproducibility_tuple() -> None:
    """Require every caller-known coordinate needed to select one owner record."""
    parameters = set(
        signature(
            FinalAnalysisWeightAuthorityReadPort.read_final_analysis_weight_authority
        ).parameters
    )

    required_lookup_coordinates = {
        "tenant_record_id",
        "validity_study_id",
        "analysis_weight_receipt_reference",
        "analysis_weight_receipt_digest",
        "evidence_version",
        "estimand_reference",
        "estimand_digest",
        "estimand_scope_code",
        "target_population_reference",
        "target_population_digest",
        "analysis_unit_code",
        "analysis_window_reference",
        "reference_duration_reference",
        "reference_duration_digest",
        "eligible_case_set_digest",
        "analytic_case_occurrence_set_digest",
        "source_universe_receipt_reference",
        "source_universe_receipt_version",
        "source_universe_receipt_digest",
        "sampling_design_receipt_reference",
        "sampling_design_receipt_version",
        "sampling_design_receipt_digest",
        "base_weight_method_code",
        "base_weight_method_version",
        "base_weight_evidence_digest",
        "base_weight_artifact_digest",
        "adjustments",
        "final_weight_artifact_digest",
        "weight_eligibility_receipt_reference",
        "weight_eligibility_receipt_digest",
        "analytic_case_count",
        "constructed_at",
        "correction_sequence",
        "supersedes_receipt_digest",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
    }
    assert required_lookup_coordinates <= parameters

    owner_resolved_chronology = {
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
    }
    assert parameters.isdisjoint(owner_resolved_chronology)
