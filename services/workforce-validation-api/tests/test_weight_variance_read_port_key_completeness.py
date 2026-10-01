"""Require the owner read to key the complete point-weight/variance compatibility tuple."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.variance_authority import (
    WeightVarianceAuthorityRecord,
    resolve_weight_variance_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
SAMPLING_REFERENCE = "sampling_design_receipt:22222222-2222-4222-8222-222222222222"
VARIANCE_REFERENCE = "variance_design_receipt:33333333-3333-4333-8333-333333333333"
METHOD_REFERENCE = "variance_method:44444444-4444-4444-8444-444444444444"
OWNER_REFERENCE = "released_owner_contract:55555555-5555-4555-8555-555555555555"
AUTHORITY_REFERENCE = "variance_compatibility_authority:11111111-1111-4111-8111-111111111111"
SAMPLING_DIGEST = "1" * 64
ANALYSIS_WEIGHT_DIGEST = "2" * 64
CASE_SET_DIGEST = "3" * 64
ELIGIBILITY_DIGEST = "4" * 64
FINAL_WEIGHT_DIGEST = "6" * 64
VARIANCE_DIGEST = "7" * 64
OWNER_DIGEST = "8" * 64
RELEASED_AT = datetime(2026, 9, 17, 1, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 2, tzinfo=timezone.utc)


class _StrictReadPort:
    """Require every coordinate needed to select one compatibility record."""

    def read_weight_variance_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        sampling_receipt_reference: str,
        sampling_receipt_version: int,
        sampling_receipt_digest: str,
        analysis_weight_receipt_digest: str,
        analytic_case_occurrence_set_digest: str,
        weight_eligibility_receipt_digest: str,
        weight_correction_sequence: int,
        final_weight_artifact_digest: str,
        variance_design_receipt_reference: str,
        variance_design_receipt_version: int,
        variance_design_receipt_digest: str,
        variance_method_reference: str,
        variance_method_version: int,
        variance_evidence_mode: str,
        variance_semantics: str,
        owner_contract_reference: str,
        owner_contract_version: int,
    ) -> WeightVarianceAuthorityRecord:
        assert analytic_case_occurrence_set_digest == CASE_SET_DIGEST
        assert weight_eligibility_receipt_digest == ELIGIBILITY_DIGEST
        assert weight_correction_sequence == 9
        assert final_weight_artifact_digest == FINAL_WEIGHT_DIGEST
        assert variance_method_reference == METHOD_REFERENCE
        assert variance_method_version == 2
        assert variance_evidence_mode == "replicate_weights"
        assert variance_semantics == "exact"
        return WeightVarianceAuthorityRecord(
            tenant_record_id=tenant_record_id,
            validity_study_id=validity_study_id,
            authority_reference=AUTHORITY_REFERENCE,
            sampling_receipt_reference=sampling_receipt_reference,
            sampling_receipt_version=sampling_receipt_version,
            sampling_receipt_digest=sampling_receipt_digest,
            analysis_weight_receipt_digest=analysis_weight_receipt_digest,
            analytic_case_occurrence_set_digest=analytic_case_occurrence_set_digest,
            weight_eligibility_receipt_digest=weight_eligibility_receipt_digest,
            weight_correction_sequence=weight_correction_sequence,
            final_weight_artifact_digest=final_weight_artifact_digest,
            variance_design_receipt_reference=variance_design_receipt_reference,
            variance_design_receipt_version=variance_design_receipt_version,
            variance_design_receipt_digest=variance_design_receipt_digest,
            variance_method_reference=variance_method_reference,
            variance_method_version=variance_method_version,
            variance_evidence_mode=variance_evidence_mode,
            variance_semantics=variance_semantics,
            owner_contract_reference=owner_contract_reference,
            owner_contract_version=owner_contract_version,
            owner_contract_digest=OWNER_DIGEST,
            owner_contract_released_at=RELEASED_AT,
            released_at=RELEASED_AT,
        )


def test_owner_read_receives_complete_compatibility_tuple() -> None:
    principal = ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )
    policy = PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="weight-variance-authority-read-v2",
        resource_kind="weight_variance_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=frozenset(
            {
                "authority_reference",
                "sampling_receipt_reference",
                "sampling_receipt_version",
                "sampling_receipt_digest",
                "analysis_weight_receipt_digest",
                "analytic_case_occurrence_set_digest",
                "weight_eligibility_receipt_digest",
                "weight_correction_sequence",
                "final_weight_artifact_digest",
                "variance_design_receipt_reference",
                "variance_design_receipt_version",
                "variance_design_receipt_digest",
                "variance_method_reference",
                "variance_method_version",
                "variance_evidence_mode",
                "variance_semantics",
                "owner_contract_reference",
                "owner_contract_version",
                "owner_contract_digest",
                "owner_contract_released_at",
                "released_at",
                "superseded_at",
            }
        ),
    )

    view = resolve_weight_variance_authority(
        principal=principal,
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        sampling_receipt_reference=SAMPLING_REFERENCE,
        sampling_receipt_version=3,
        sampling_receipt_digest=SAMPLING_DIGEST,
        analysis_weight_receipt_digest=ANALYSIS_WEIGHT_DIGEST,
        analytic_case_occurrence_set_digest=CASE_SET_DIGEST,
        weight_eligibility_receipt_digest=ELIGIBILITY_DIGEST,
        weight_correction_sequence=9,
        final_weight_artifact_digest=FINAL_WEIGHT_DIGEST,
        variance_design_receipt_reference=VARIANCE_REFERENCE,
        variance_design_receipt_version=5,
        variance_design_receipt_digest=VARIANCE_DIGEST,
        variance_method_reference=METHOD_REFERENCE,
        variance_method_version=2,
        variance_evidence_mode="replicate_weights",
        variance_semantics="exact",
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=4,
        used_at=USED_AT,
        purpose_code="selection_validity_analysis",
        policy=policy,
        read_port=_StrictReadPort(),
    )

    assert dict(view.fields)["variance_method_reference"] == METHOD_REFERENCE
