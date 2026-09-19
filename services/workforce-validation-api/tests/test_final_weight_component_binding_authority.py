"""Contracts for exact typed-component resolution behind final analysis weights."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy

from orgmetra_workforce_validation_api import ValidationPrincipal
import orgmetra_workforce_validation_api.final_weight_component_binding_authority as target
from orgmetra_workforce_validation_api.final_weight_component_binding_authority import (
    FinalWeightAdjustmentEvidenceBinding,
    FinalWeightComponentBindingAuthorityIntegrityError,
    FinalWeightComponentBindingAuthorityNotFound,
    FinalWeightComponentBindingAuthorityReadPort,
    FinalWeightComponentBindingAuthorityRecord,
    FinalWeightComponentBindingAuthorityView,
    resolve_final_weight_component_binding_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")
OWNER_RELEASED_AT = datetime(2026, 9, 19, 4, 0, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 19, 4, 10, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 19, 4, 30, tzinfo=timezone.utc)


class _ReadPort:
    """Return configured owner evidence and retain the deterministic lookup key."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def read_final_weight_component_binding_authority(self, **kwargs: object) -> object:
        """Return configured evidence after recording caller-known lookup coordinates."""
        self.calls.append(kwargs)
        return self.result


def _principal() -> ValidationPrincipal:
    return ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy() -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="final-weight-component-binding-read-v1",
        resource_kind="final_weight_component_binding_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=target._READ_FIELDS,
    )


def _binding(
    *,
    sequence_number: int = 1,
    evidence_kind: str = "nonresponse_adjustment_receipt",
    evidence_receipt_reference: str = (
        "nonresponse_adjustment_receipt:11111111-1111-4111-8111-111111111111"
    ),
    evidence_version: int = 1,
    evidence_receipt_digest: str = "a" * 64,
) -> FinalWeightAdjustmentEvidenceBinding:
    return FinalWeightAdjustmentEvidenceBinding(
        sequence_number=sequence_number,
        evidence_kind=evidence_kind,
        evidence_receipt_reference=evidence_receipt_reference,
        evidence_version=evidence_version,
        evidence_receipt_digest=evidence_receipt_digest,
    )


def _record(**overrides: object) -> FinalWeightComponentBindingAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "analysis_weight_receipt_reference": (
            "analysis_weight_receipt:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        ),
        "analysis_weight_receipt_digest": "1" * 64,
        "analysis_weight_evidence_version": 1,
        "binding_reference": (
            "final_weight_component_binding:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        ),
        "binding_digest": "2" * 64,
        "binding_version": 1,
        "base_weight_evidence_receipt_reference": (
            "base_weight_evidence_receipt:cccccccc-cccc-4ccc-8ccc-cccccccccccc"
        ),
        "base_weight_evidence_receipt_digest": "3" * 64,
        "base_weight_evidence_version": 1,
        "adjustment_bindings": (_binding(),),
        "owner_contract_reference": (
            "released_owner_contract:dddddddd-dddd-4ddd-8ddd-dddddddddddd"
        ),
        "owner_contract_version": 1,
        "owner_contract_digest": "4" * 64,
        "owner_contract_released_at": OWNER_RELEASED_AT,
        "released_at": RELEASED_AT,
        "superseded_at": None,
    }
    values.update(overrides)
    return FinalWeightComponentBindingAuthorityRecord(**values)


def _resolve(
    result: object,
    *,
    used_at: datetime = USED_AT,
    read_port: _ReadPort | None = None,
    **overrides: object,
) -> tuple[object, _ReadPort]:
    port = _ReadPort(result) if read_port is None else read_port
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "analysis_weight_receipt_reference": (
            "analysis_weight_receipt:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        ),
        "analysis_weight_receipt_digest": "1" * 64,
        "analysis_weight_evidence_version": 1,
        "used_at": used_at,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": port,
    }
    values.update(overrides)
    return resolve_final_weight_component_binding_authority(**values), port


def test_resolver_returns_exact_component_locator_and_uses_final_receipt_key_only() -> None:
    record = _record()
    view, port = _resolve(record)

    fields = dict(view.fields)
    assert fields["base_weight_evidence_receipt_reference"] == (
        "base_weight_evidence_receipt:cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    )
    bindings = fields["adjustment_bindings"]
    assert type(bindings) is tuple
    assert bindings[0].evidence_receipt_reference == (
        "nonresponse_adjustment_receipt:11111111-1111-4111-8111-111111111111"
    )
    assert port.calls == [
        {
            "tenant_record_id": TENANT,
            "validity_study_id": STUDY,
            "analysis_weight_receipt_reference": (
                "analysis_weight_receipt:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
            ),
            "analysis_weight_receipt_digest": "1" * 64,
            "analysis_weight_evidence_version": 1,
        }
    ]


def test_binding_sequence_may_skip_generic_adjustments_but_must_increase() -> None:
    bindings = (
        _binding(),
        _binding(
            sequence_number=3,
            evidence_kind="trimming_bounding_adjustment_receipt",
            evidence_receipt_reference=(
                "trimming_bounding_adjustment_receipt:22222222-2222-4222-8222-222222222222"
            ),
            evidence_receipt_digest="b" * 64,
        ),
    )
    record = _record(adjustment_bindings=bindings)
    assert dict(record.fields)["adjustment_bindings"] == bindings

    with pytest.raises(ValueError, match="strictly increasing"):
        _record(adjustment_bindings=(bindings[1], bindings[0]))


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"analysis_weight_evidence_version": 2}, "analysis_weight_evidence_version"),
        ({"binding_version": 2}, "binding_version"),
        ({"base_weight_evidence_version": 2}, "base_weight_evidence_version"),
        ({"adjustment_bindings": [_binding()]}, "immutable tuple"),
        (
            {"owner_contract_released_at": RELEASED_AT + timedelta(seconds=1)},
            "owner contract",
        ),
        (
            {"superseded_at": RELEASED_AT},
            "superseded_at",
        ),
    ],
)
def test_record_rejects_noncanonical_contract_shapes(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _record(**overrides)


@pytest.mark.parametrize(
    ("kind", "reference"),
    [
        (
            "unknown_adjustment_receipt",
            "nonresponse_adjustment_receipt:11111111-1111-4111-8111-111111111111",
        ),
        (
            "calibration_adjustment_receipt",
            "nonresponse_adjustment_receipt:11111111-1111-4111-8111-111111111111",
        ),
    ],
)
def test_adjustment_binding_rejects_unknown_kind_or_wrong_receipt_namespace(
    kind: str, reference: str
) -> None:
    with pytest.raises(ValueError):
        _binding(evidence_kind=kind, evidence_receipt_reference=reference)


def test_adjustment_binding_rejects_non_v1_evidence() -> None:
    with pytest.raises(ValueError, match="evidence_version"):
        _binding(evidence_version=2)


def test_forged_nested_binding_cannot_hide_trailing_state() -> None:
    canonical = _binding()
    forged = tuple.__new__(
        FinalWeightAdjustmentEvidenceBinding,
        tuple(canonical) + ("hidden-component-coordinate",),
    )
    with pytest.raises(ValueError, match="canonical"):
        _record(adjustment_bindings=(forged,))


def test_forged_outer_record_maps_to_integrity_error() -> None:
    canonical = _record()
    forged = tuple.__new__(
        FinalWeightComponentBindingAuthorityRecord,
        tuple(canonical) + ("hidden-owner-coordinate",),
    )
    with pytest.raises(FinalWeightComponentBindingAuthorityIntegrityError):
        _resolve(forged)


def test_truncated_outer_record_maps_to_integrity_error() -> None:
    canonical = _record()
    forged = tuple.__new__(
        FinalWeightComponentBindingAuthorityRecord,
        tuple(canonical)[:-1],
    )
    with pytest.raises(FinalWeightComponentBindingAuthorityIntegrityError):
        _resolve(forged)


def test_wrong_target_and_authority_interval_fail_closed() -> None:
    with pytest.raises(FinalWeightComponentBindingAuthorityIntegrityError, match="target"):
        _resolve(_record(tenant_record_id=OTHER_TENANT))
    with pytest.raises(FinalWeightComponentBindingAuthorityIntegrityError, match="before"):
        _resolve(_record(), used_at=RELEASED_AT - timedelta(microseconds=1))
    cutover = USED_AT
    with pytest.raises(FinalWeightComponentBindingAuthorityIntegrityError, match="supersession"):
        _resolve(_record(superseded_at=cutover), used_at=cutover)


def test_not_found_and_noncanonical_owner_types_fail_closed() -> None:
    with pytest.raises(FinalWeightComponentBindingAuthorityNotFound):
        _resolve(None)
    with pytest.raises(FinalWeightComponentBindingAuthorityIntegrityError, match="non-canonical"):
        _resolve(object())


def test_principal_policy_and_protocol_placeholder_are_not_accepted() -> None:
    with pytest.raises(TypeError, match="principal"):
        _resolve(_record(), principal=object())
    with pytest.raises(TypeError, match="policy"):
        _resolve(_record(), policy=object())

    class _ProtocolOnly(FinalWeightComponentBindingAuthorityReadPort):
        pass

    with pytest.raises(TypeError, match="statically callable"):
        resolve_final_weight_component_binding_authority(
            principal=_principal(),
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            analysis_weight_receipt_reference=(
                "analysis_weight_receipt:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
            ),
            analysis_weight_receipt_digest="1" * 64,
            analysis_weight_evidence_version=1,
            used_at=USED_AT,
            purpose_code="selection_validity_analysis",
            policy=_policy(),
            read_port=_ProtocolOnly(),
        )


def test_public_view_constructor_is_non_issuing() -> None:
    with pytest.raises(TypeError, match="issued only"):
        FinalWeightComponentBindingAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )
