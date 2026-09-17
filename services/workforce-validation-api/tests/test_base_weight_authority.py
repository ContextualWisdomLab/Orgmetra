"""Fail-closed contract for released base/design-weight provenance."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.base_weight_authority import (
    BaseWeightAuthorityIntegrityError,
    BaseWeightAuthorityNotFound,
    BaseWeightAuthorityReadPort,
    BaseWeightAuthorityRecord,
    BaseWeightAuthorityView,
    resolve_base_weight_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000f2")
BASE_RECEIPT_REFERENCE = "base_weight_evidence_receipt:11111111-1111-4111-8111-111111111111"
SOURCE_REFERENCE = "source_universe_receipt:22222222-2222-4222-8222-222222222222"
SAMPLING_REFERENCE = "sampling_design_receipt:33333333-3333-4333-8333-333333333333"
OWNER_REFERENCE = "released_owner_contract:44444444-4444-4444-8444-444444444444"
BASE_RECEIPT_DIGEST = "1" * 64
SOURCE_DIGEST = "2" * 64
SAMPLING_DIGEST = "3" * 64
SAMPLED_SET_DIGEST = "4" * 64
SELECTION_PROBABILITY_SET_DIGEST = "5" * 64
BASE_ARTIFACT_DIGEST = "6" * 64
OWNER_DIGEST = "7" * 64
SOURCE_RELEASED_AT = datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc)
SAMPLING_RELEASED_AT = datetime(2026, 9, 17, 6, 30, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 17, 6, 45, tzinfo=timezone.utc)
CONSTRUCTED_AT = datetime(2026, 9, 17, 7, 0, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 7, 30, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "base_weight_evidence_receipt_reference",
        "base_weight_evidence_receipt_digest",
        "evidence_version",
        "source_universe_receipt_reference",
        "source_universe_receipt_version",
        "source_universe_receipt_digest",
        "source_universe_released_at",
        "sampling_design_receipt_reference",
        "sampling_design_receipt_version",
        "sampling_design_receipt_digest",
        "sampling_design_released_at",
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
        "owner_contract_released_at",
        "released_at",
    }
)


class _ReadPort:
    """Return configured owner evidence and capture lookup coordinates."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def read_base_weight_authority(self, **coordinates: object) -> object:
        self.calls.append(dict(coordinates))
        return self.result


class _ProtocolOnly(BaseWeightAuthorityReadPort):
    """Inherit only the Protocol placeholder."""


class _DescriptorReadPort:
    """Expose a descriptor that must never execute."""

    @property
    def read_base_weight_authority(self) -> object:
        raise AssertionError("descriptor must not execute")


class _NoReadMethod:
    """Deliberately omit the owner capability."""


def _principal(*, tenant_record_id: UUID = TENANT) -> ValidationPrincipal:
    return ValidationPrincipal(
        tenant_record_id=tenant_record_id,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy(*, purpose_code: str = "selection_validity_analysis") -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="base-weight-authority-read-v1",
        resource_kind="base_weight_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(**overrides: object) -> BaseWeightAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "base_weight_evidence_receipt_reference": BASE_RECEIPT_REFERENCE,
        "base_weight_evidence_receipt_digest": BASE_RECEIPT_DIGEST,
        "evidence_version": 1,
        "source_universe_receipt_reference": SOURCE_REFERENCE,
        "source_universe_receipt_version": 4,
        "source_universe_receipt_digest": SOURCE_DIGEST,
        "source_universe_released_at": SOURCE_RELEASED_AT,
        "sampling_design_receipt_reference": SAMPLING_REFERENCE,
        "sampling_design_receipt_version": 3,
        "sampling_design_receipt_digest": SAMPLING_DIGEST,
        "sampling_design_released_at": SAMPLING_RELEASED_AT,
        "sampled_occurrence_set_digest": SAMPLED_SET_DIGEST,
        "selection_probability_set_digest": SELECTION_PROBABILITY_SET_DIGEST,
        "selection_stage_count": 2,
        "base_weight_method_code": "inverse_inclusion_probability",
        "base_weight_method_version": 1,
        "base_weight_artifact_digest": BASE_ARTIFACT_DIGEST,
        "constructed_at": CONSTRUCTED_AT,
        "owner_contract_reference": OWNER_REFERENCE,
        "owner_contract_version": 6,
        "owner_contract_digest": OWNER_DIGEST,
        "owner_contract_released_at": OWNER_CONTRACT_RELEASED_AT,
        "released_at": RELEASED_AT,
    }
    values.update(overrides)
    return BaseWeightAuthorityRecord(**values)


def _resolve(*, read_port: object, **overrides: object) -> BaseWeightAuthorityView:
    values = dict(_record().fields)
    for owner_resolved_field in (
        "source_universe_released_at",
        "sampling_design_released_at",
        "owner_contract_released_at",
    ):
        values.pop(owner_resolved_field)
    values.update(
        {
            "principal": _principal(),
            "tenant_record_id": TENANT,
            "validity_study_id": STUDY,
            "used_at": USED_AT,
            "purpose_code": "selection_validity_analysis",
            "policy": _policy(),
            "read_port": read_port,
        }
    )
    values.update(overrides)
    return resolve_base_weight_authority(**values)


def test_resolution_binds_sampling_stage_probabilities_to_base_weight_artifact() -> None:
    port = _ReadPort(_record())

    view = _resolve(read_port=port)

    assert isinstance(port, BaseWeightAuthorityReadPort)
    assert len(port.calls) == 1
    assert port.calls[0]["source_universe_receipt_version"] == 4
    assert port.calls[0]["sampling_design_receipt_version"] == 3
    assert port.calls[0]["selection_probability_set_digest"] == SELECTION_PROBABILITY_SET_DIGEST
    assert "source_universe_released_at" not in port.calls[0]
    assert "sampling_design_released_at" not in port.calls[0]
    assert "owner_contract_released_at" not in port.calls[0]
    assert ("sampled_occurrence_set_digest", SAMPLED_SET_DIGEST) in view.fields
    assert ("selection_stage_count", 2) in view.fields
    assert ("base_weight_artifact_digest", BASE_ARTIFACT_DIGEST) in view.fields
    assert ("source_universe_released_at", SOURCE_RELEASED_AT) in view.fields
    assert ("sampling_design_released_at", SAMPLING_RELEASED_AT) in view.fields
    assert ("owner_contract_released_at", OWNER_CONTRACT_RELEASED_AT) in view.fields
    assert ("released_at", RELEASED_AT) in view.fields


def test_prerequisite_releases_are_resolved_from_owner_evidence() -> None:
    source_release = SOURCE_RELEASED_AT + timedelta(seconds=1)
    sampling_release = SAMPLING_RELEASED_AT + timedelta(seconds=1)
    owner_release = OWNER_CONTRACT_RELEASED_AT + timedelta(seconds=1)
    view = _resolve(
        read_port=_ReadPort(
            _record(
                source_universe_released_at=source_release,
                sampling_design_released_at=sampling_release,
                owner_contract_released_at=owner_release,
            )
        )
    )

    assert ("source_universe_released_at", source_release) in view.fields
    assert ("sampling_design_released_at", sampling_release) in view.fields
    assert ("owner_contract_released_at", owner_release) in view.fields


def test_authorization_denial_happens_before_owner_resolution() -> None:
    port = _ReadPort(_record())
    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))
    assert port.calls == []


def test_missing_noncanonical_or_mismatched_owner_evidence_fails_closed() -> None:
    with pytest.raises(BaseWeightAuthorityNotFound):
        _resolve(read_port=_ReadPort(None))
    with pytest.raises(BaseWeightAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))
    with pytest.raises(BaseWeightAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(selection_stage_count=3)))
    with pytest.raises(BaseWeightAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(base_weight_artifact_digest="8" * 64)))
    with pytest.raises(BaseWeightAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(tenant_record_id=OTHER_TENANT)))
    with pytest.raises(BaseWeightAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(validity_study_id=OTHER_STUDY)))


def test_source_sampling_and_release_chronology_fail_closed() -> None:
    with pytest.raises(ValueError):
        _record(source_universe_released_at=CONSTRUCTED_AT + timedelta(seconds=1))
    with pytest.raises(ValueError):
        _record(sampling_design_released_at=CONSTRUCTED_AT + timedelta(seconds=1))
    with pytest.raises(ValueError):
        _record(released_at=CONSTRUCTED_AT - timedelta(seconds=1))
    with pytest.raises(ValueError, match="owner contract"):
        _record(owner_contract_released_at=RELEASED_AT + timedelta(seconds=1))
    with pytest.raises(BaseWeightAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(released_at=USED_AT + timedelta(seconds=1))))


@pytest.mark.parametrize(
    ("key", "value", "error"),
    [
        ("principal", object(), TypeError),
        ("policy", object(), TypeError),
        ("read_port", _NoReadMethod(), TypeError),
        ("read_port", _ProtocolOnly(), TypeError),
        ("read_port", _DescriptorReadPort(), TypeError),
        ("tenant_record_id", "not-a-uuid", ValueError),
        ("validity_study_id", UUID(int=0), ValueError),
        ("base_weight_evidence_receipt_reference", "wrong:receipt", ValueError),
        ("base_weight_evidence_receipt_digest", "ABC", ValueError),
        ("evidence_version", False, ValueError),
        ("evidence_version", 2, ValueError),
        ("source_universe_receipt_reference", "wrong:source", ValueError),
        ("source_universe_receipt_version", 0, ValueError),
        ("source_universe_receipt_digest", "2" * 63, ValueError),
        ("sampling_design_receipt_reference", "wrong:sampling", ValueError),
        ("sampling_design_receipt_version", False, ValueError),
        ("sampling_design_receipt_digest", "3" * 63, ValueError),
        ("sampled_occurrence_set_digest", "4" * 63, ValueError),
        ("selection_probability_set_digest", "5" * 63, ValueError),
        ("selection_stage_count", 0, ValueError),
        ("base_weight_method_code", "Inverse Probability", ValueError),
        ("base_weight_method_version", False, ValueError),
        ("base_weight_artifact_digest", "6" * 63, ValueError),
        ("owner_contract_reference", "wrong:owner", ValueError),
        ("owner_contract_version", 0, ValueError),
        ("owner_contract_digest", "7" * 63, ValueError),
    ],
)
def test_hostile_coordinates_fail_closed(key: str, value: object, error: type[Exception]) -> None:
    with pytest.raises(error):
        _resolve(read_port=_ReadPort(_record()), **{key: value})


def test_view_cannot_be_constructed_directly() -> None:
    with pytest.raises(TypeError):
        BaseWeightAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )