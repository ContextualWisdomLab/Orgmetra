"""Fail-closed contract for released trimming/bounding adjustment authority."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.trimming_bounding_authority import (
    TrimmingBoundingAuthorityIntegrityError,
    TrimmingBoundingAuthorityNotFound,
    TrimmingBoundingAuthorityReadPort,
    TrimmingBoundingAuthorityRecord,
    TrimmingBoundingAuthorityView,
    resolve_trimming_bounding_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000d2")
RECEIPT_REFERENCE = "trimming_bounding_adjustment_receipt:11111111-1111-4111-8111-111111111111"
RULE_REFERENCE = "weight_trimming_rule:winsor-p995-v1"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
RECEIPT_DIGEST = "1" * 64
RULE_CONFIGURATION_DIGEST = "2" * 64
AFFECTED_CASE_SET_DIGEST = "3" * 64
INPUT_WEIGHT_DIGEST = "4" * 64
OUTPUT_WEIGHT_DIGEST = "5" * 64
OWNER_CONTRACT_DIGEST = "6" * 64
CONSTRUCTED_AT = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 16, 12, 30, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "adjustment_receipt_reference",
        "adjustment_receipt_digest",
        "evidence_version",
        "rule_reference",
        "rule_version",
        "rule_configuration_digest",
        "affected_case_occurrence_set_digest",
        "affected_case_count",
        "input_weight_artifact_digest",
        "output_weight_artifact_digest",
        "constructed_at",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
    }
)


class _ReadPort:
    """Return configured trimming authority and retain lookup coordinates."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def read_trimming_bounding_authority(self, **coordinates: object) -> object:
        """Capture the owner lookup and return configured evidence."""
        self.calls.append(dict(coordinates))
        return self.result


class _NoReadMethod:
    """Deliberately fail the owner-port protocol."""


class _ProtocolOnly(TrimmingBoundingAuthorityReadPort):
    """Inherit only the Protocol placeholder, not a concrete owner capability."""


class _DescriptorReadPort:
    """Expose a descriptor that must be rejected without executing it."""

    @property
    def read_trimming_bounding_authority(self) -> object:
        raise AssertionError("descriptor must not execute")


def _principal() -> ValidationPrincipal:
    return ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy(*, purpose_code: str = "selection_validity_analysis") -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="trimming-bounding-authority-read-v1",
        resource_kind="trimming_bounding_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(**overrides: object) -> TrimmingBoundingAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "adjustment_receipt_reference": RECEIPT_REFERENCE,
        "adjustment_receipt_digest": RECEIPT_DIGEST,
        "evidence_version": 1,
        "rule_reference": RULE_REFERENCE,
        "rule_version": 2,
        "rule_configuration_digest": RULE_CONFIGURATION_DIGEST,
        "affected_case_occurrence_set_digest": AFFECTED_CASE_SET_DIGEST,
        "affected_case_count": 17,
        "input_weight_artifact_digest": INPUT_WEIGHT_DIGEST,
        "output_weight_artifact_digest": OUTPUT_WEIGHT_DIGEST,
        "constructed_at": CONSTRUCTED_AT,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 3,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "owner_contract_released_at": OWNER_CONTRACT_RELEASED_AT,
        "released_at": RELEASED_AT,
    }
    values.update(overrides)
    return TrimmingBoundingAuthorityRecord(**values)


def _resolve(*, read_port: object, **overrides: object) -> TrimmingBoundingAuthorityView:
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "adjustment_receipt_reference": RECEIPT_REFERENCE,
        "adjustment_receipt_digest": RECEIPT_DIGEST,
        "evidence_version": 1,
        "rule_reference": RULE_REFERENCE,
        "rule_version": 2,
        "rule_configuration_digest": RULE_CONFIGURATION_DIGEST,
        "affected_case_occurrence_set_digest": AFFECTED_CASE_SET_DIGEST,
        "affected_case_count": 17,
        "input_weight_artifact_digest": INPUT_WEIGHT_DIGEST,
        "output_weight_artifact_digest": OUTPUT_WEIGHT_DIGEST,
        "constructed_at": CONSTRUCTED_AT,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 3,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_trimming_bounding_authority(**values)


def test_resolution_binds_rule_affected_cases_and_artifact_lineage() -> None:
    port = _ReadPort(_record())
    view = _resolve(read_port=port)

    assert isinstance(port, TrimmingBoundingAuthorityReadPort)
    assert len(port.calls) == 1
    assert port.calls[0]["rule_reference"] == RULE_REFERENCE
    assert port.calls[0]["affected_case_occurrence_set_digest"] == AFFECTED_CASE_SET_DIGEST
    assert port.calls[0]["affected_case_count"] == 17
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    assert ("rule_reference", RULE_REFERENCE) in view.fields
    assert ("rule_version", 2) in view.fields
    assert ("affected_case_count", 17) in view.fields
    assert ("affected_case_occurrence_set_digest", AFFECTED_CASE_SET_DIGEST) in view.fields
    assert ("output_weight_artifact_digest", OUTPUT_WEIGHT_DIGEST) in view.fields
    assert ("owner_contract_released_at", OWNER_CONTRACT_RELEASED_AT) in view.fields
    assert ("superseded_at", None) in view.fields


def test_authorization_denial_happens_before_owner_resolution() -> None:
    port = _ReadPort(_record())
    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))
    assert port.calls == []


def test_missing_or_noncanonical_owner_evidence_fails_closed() -> None:
    with pytest.raises(TrimmingBoundingAuthorityNotFound):
        _resolve(read_port=_ReadPort(None))
    with pytest.raises(TrimmingBoundingAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))


@pytest.mark.parametrize(
    "record_overrides",
    [
        {"tenant_record_id": OTHER_TENANT},
        {"validity_study_id": OTHER_STUDY},
        {"adjustment_receipt_digest": "a" * 64},
        {"rule_reference": "weight_trimming_rule:other"},
        {"rule_version": 3},
        {"rule_configuration_digest": "b" * 64},
        {"affected_case_occurrence_set_digest": "c" * 64},
        {"affected_case_count": 18},
        {"input_weight_artifact_digest": "d" * 64},
        {"output_weight_artifact_digest": "e" * 64},
        {"constructed_at": CONSTRUCTED_AT + timedelta(seconds=1)},
        {"owner_contract_version": 4},
        {"owner_contract_digest": "f" * 64},
    ],
)
def test_owner_evidence_must_match_every_requested_coordinate(
    record_overrides: dict[str, object]
) -> None:
    with pytest.raises(TrimmingBoundingAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(**record_overrides)))


def test_artifact_release_and_currentness_chronology_fail_closed() -> None:
    with pytest.raises(ValueError):
        _record(output_weight_artifact_digest=INPUT_WEIGHT_DIGEST)
    with pytest.raises(ValueError):
        _record(released_at=CONSTRUCTED_AT - timedelta(seconds=1))
    with pytest.raises(ValueError, match="superseded_at must be later"):
        _record(superseded_at=RELEASED_AT)
    with pytest.raises(ValueError, match="standard-library timezone provider"):
        _record(superseded_at=datetime(2026, 9, 16, 14, 0))
    with pytest.raises(TrimmingBoundingAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(released_at=USED_AT + timedelta(seconds=1))))

    cutover = RELEASED_AT + timedelta(hours=1)
    historical = _resolve(
        read_port=_ReadPort(_record(superseded_at=cutover)),
        used_at=cutover - timedelta(seconds=1),
    )
    assert ("superseded_at", cutover) in historical.fields
    with pytest.raises(
        TrimmingBoundingAuthorityIntegrityError,
        match="superseded for this scientific-use instant",
    ):
        _resolve(
            read_port=_ReadPort(_record(superseded_at=cutover)),
            used_at=cutover,
        )


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
        ("adjustment_receipt_reference", "wrong:receipt", ValueError),
        ("adjustment_receipt_digest", "ABC", ValueError),
        ("evidence_version", False, ValueError),
        ("rule_reference", "wrong:rule", ValueError),
        ("rule_version", 0, ValueError),
        ("rule_configuration_digest", "2" * 63, ValueError),
        ("affected_case_occurrence_set_digest", "3" * 65, ValueError),
        ("affected_case_count", True, ValueError),
        ("input_weight_artifact_digest", "4" * 63, ValueError),
        ("output_weight_artifact_digest", "5" * 65, ValueError),
        ("constructed_at", datetime(2026, 9, 16, 12, 0), ValueError),
        ("owner_contract_reference", "wrong:contract", ValueError),
        ("owner_contract_version", 0, ValueError),
        ("owner_contract_digest", "6" * 63, ValueError),
        ("used_at", datetime(2026, 9, 17), ValueError),
        ("purpose_code", "Selection Validity Analysis", ValueError),
    ],
)
def test_invalid_request_or_dependency_fails_before_owner_resolution(
    key: str, value: object, error: type[Exception]
) -> None:
    port: object = _ReadPort(_record())
    overrides = {key: value}
    if key == "read_port":
        port = value
        overrides = {}
    with pytest.raises(error):
        _resolve(read_port=port, **overrides)
    if isinstance(port, _ReadPort):
        assert port.calls == []


def test_record_and_view_are_structurally_immutable_and_uuid_views_are_detached() -> None:
    tenant = UUID(str(TENANT))
    record = _record(tenant_record_id=tenant)
    object.__setattr__(tenant, "int", OTHER_TENANT.int)
    assert record.tenant_record_id == TENANT
    with pytest.raises(AttributeError):
        object.__setattr__(record, "affected_case_count", 18)

    view = _resolve(read_port=_ReadPort(record))
    returned_tenant = view.tenant_record_id
    object.__setattr__(returned_tenant, "int", OTHER_TENANT.int)
    assert view.tenant_record_id == TENANT
    with pytest.raises(AttributeError):
        object.__setattr__(view, "fields", ())
    with pytest.raises(TypeError):
        TrimmingBoundingAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )


def test_view_rejects_tuple_base_constructor_forgery() -> None:
    """Reject caller-authored instances created through the tuple base class."""
    with pytest.raises(TypeError):
        tuple.__new__(
            TrimmingBoundingAuthorityView,
            (TENANT, STUDY, (("affected_case_count", 17),)),
        )


def test_raw_view_allocation_cannot_expose_projection_state() -> None:
    """Keep an unissued raw allocation unusable through every public property."""
    forged = object.__new__(TrimmingBoundingAuthorityView)

    with pytest.raises(TrimmingBoundingAuthorityIntegrityError):
        _ = forged.tenant_record_id
    with pytest.raises(TrimmingBoundingAuthorityIntegrityError):
        _ = forged.validity_study_id
    with pytest.raises(TrimmingBoundingAuthorityIntegrityError):
        _ = forged.fields


def test_view_rejects_caller_authored_issuance_marker() -> None:
    """Reject a raw allocation even when a caller invents a marker value."""
    forged = object.__new__(TrimmingBoundingAuthorityView)
    object.__setattr__(forged, "_tenant_identity", TENANT)
    object.__setattr__(forged, "_study_identity", STUDY)
    object.__setattr__(forged, "_fields", ())
    object.__setattr__(forged, "_issuance_marker", object())

    with pytest.raises(TrimmingBoundingAuthorityIntegrityError):
        _ = forged.fields


def test_issued_view_rejects_mutation_and_deletion() -> None:
    """Keep a resolver-issued view immutable after all owner checks complete."""
    view = _resolve(read_port=_ReadPort(_record()))

    with pytest.raises(AttributeError):
        view._fields = ()
    with pytest.raises(AttributeError):
        del view._fields
