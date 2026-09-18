"""Exact-artifact correction contract for non-reproducible validation evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api.registry import ValidationPrincipal
from orgmetra_workforce_validation_api.result_nonverifiability import (
    ValidationResultNonVerifiabilityRecord,
)
from orgmetra_workforce_validation_api.result_nonverifiability_supersession_v2_authority import (
    ValidationResultNonVerifiabilitySupersessionV2AuthorityIntegrityError,
    ValidationResultNonVerifiabilitySupersessionV2AuthorityNotFound,
    ValidationResultNonVerifiabilitySupersessionV2AuthorityReadPort,
    ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord,
    ValidationResultNonVerifiabilitySupersessionV2AuthorityView,
    resolve_validation_result_nonverifiability_supersession_v2_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000d2")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
OTHER_RESULT_REFERENCE = "validation_analysis_result:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
FAILED_REFERENCE = "analysis_weight_receipt:22222222-2222-4222-8222-222222222222"
OTHER_FAILED_REFERENCE = "analysis_weight_receipt:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:33333333-3333-4333-8333-333333333333"
OTHER_ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:cccccccc-cccc-4ccc-8ccc-cccccccccccc"
SUCCESSOR_ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:44444444-4444-4444-8444-444444444444"
OWNER_REFERENCE = "released_owner_contract:55555555-5555-4555-8555-555555555555"
OTHER_OWNER_REFERENCE = "released_owner_contract:dddddddd-dddd-4ddd-8ddd-dddddddddddd"
RESULT_DIGEST = "1" * 64
FAILED_DIGEST = "2" * 64
ATTEMPT_DIGEST = "3" * 64
SUCCESSOR_DIGEST = "4" * 64
OWNER_DIGEST = "5" * 64
OWNER_RELEASED_AT = datetime(2026, 9, 17, 5, 55, tzinfo=timezone.utc)
FAILED_RELEASED_AT = datetime(2026, 9, 17, 5, 59, tzinfo=timezone.utc)
EVALUATED_AT = datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc)
ATTEMPT_RELEASED_AT = datetime(2026, 9, 17, 6, 2, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 6, 5, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 6, 10, tzinfo=timezone.utc)
CUTOVER = datetime(2026, 9, 17, 7, 0, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "failed_evidence_kind",
        "failure_mode",
        "failed_evidence_reference",
        "failed_evidence_digest",
        "failed_evidence_released_at",
        "verification_attempt_reference",
        "verification_attempt_digest",
        "verification_attempt_released_at",
        "evidence_version",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_target_result_reference",
        "successor_target_result_digest",
        "successor_failed_evidence_kind",
        "successor_target_failed_evidence_reference",
        "successor_target_failed_evidence_digest",
        "successor_target_failed_evidence_released_at",
        "successor_verification_attempt_reference",
        "successor_verification_attempt_digest",
        "successor_verification_attempt_released_at",
    }
)


class _ReadPort:
    """Return configured v2 authority and retain caller-known lookup coordinates."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def read_validation_result_nonverifiability_supersession_v2_authority(
        self, **coordinates: object
    ) -> object:
        """Capture the lookup before returning configured owner evidence."""
        self.calls.append(dict(coordinates))
        return self.result


class _NoReadMethod:
    """Deliberately omit the owner capability."""


class _ProtocolOnly(ValidationResultNonVerifiabilitySupersessionV2AuthorityReadPort):
    """Inherit only the Protocol placeholder."""


class _DescriptorReadPort:
    """Expose a descriptor that static capability validation must reject."""

    @property
    def read_validation_result_nonverifiability_supersession_v2_authority(self) -> object:
        """Fail if descriptor execution leaks through static validation."""
        raise AssertionError("descriptor must not execute")


def _principal(*, tenant_record_id: UUID = TENANT) -> ValidationPrincipal:
    """Return the canonical workforce-validation principal."""
    return ValidationPrincipal(
        tenant_record_id=tenant_record_id,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy(*, purpose_code: str = "selection_validity_analysis") -> PurposeBoundAccessPolicy:
    """Return the purpose-bound v2 correction policy."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="validation-result-nonverifiability-supersession-read-v2",
        resource_kind="validation_result_nonverifiability_supersession_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _predecessor(**overrides: object) -> ValidationResultNonVerifiabilityRecord:
    """Build one released non-reproducible predecessor outcome."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "result_reference": RESULT_REFERENCE,
        "result_digest": RESULT_DIGEST,
        "failed_evidence_kind": "analysis_weight_receipt",
        "failure_mode": "non_reproducible",
        "failed_evidence_reference": FAILED_REFERENCE,
        "failed_evidence_digest": FAILED_DIGEST,
        "failed_evidence_released_at": FAILED_RELEASED_AT,
        "verification_attempt_reference": ATTEMPT_REFERENCE,
        "verification_attempt_digest": ATTEMPT_DIGEST,
        "verification_attempt_released_at": ATTEMPT_RELEASED_AT,
        "owner_contract_reference": OWNER_REFERENCE,
        "owner_contract_version": 7,
        "owner_contract_digest": OWNER_DIGEST,
        "owner_contract_released_at": OWNER_RELEASED_AT,
        "evaluated_at": EVALUATED_AT,
        "released_at": RELEASED_AT,
        "superseded_at": None,
    }
    values.update(overrides)
    return ValidationResultNonVerifiabilityRecord(**values)


def _record(
    *,
    predecessor: ValidationResultNonVerifiabilityRecord | None = None,
    **overrides: object,
) -> ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord:
    """Build current v2 authority with optional owner-supplied successor coordinates."""
    values: dict[str, object] = {
        "predecessor": _predecessor() if predecessor is None else predecessor,
        "evidence_version": 2,
        "superseded_at": None,
        "successor_target_result_reference": None,
        "successor_target_result_digest": None,
        "successor_failed_evidence_kind": None,
        "successor_target_failed_evidence_reference": None,
        "successor_target_failed_evidence_digest": None,
        "successor_target_failed_evidence_released_at": None,
        "successor_verification_attempt_reference": None,
        "successor_verification_attempt_digest": None,
        "successor_verification_attempt_released_at": None,
    }
    values.update(overrides)
    return ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord(**values)


def _successor_overrides(**overrides: object) -> dict[str, object]:
    """Return the complete exact-artifact successor tuple with optional hostile changes."""
    values: dict[str, object] = {
        "superseded_at": CUTOVER,
        "successor_target_result_reference": RESULT_REFERENCE,
        "successor_target_result_digest": RESULT_DIGEST,
        "successor_failed_evidence_kind": "analysis_weight_receipt",
        "successor_target_failed_evidence_reference": FAILED_REFERENCE,
        "successor_target_failed_evidence_digest": FAILED_DIGEST,
        "successor_target_failed_evidence_released_at": FAILED_RELEASED_AT,
        "successor_verification_attempt_reference": SUCCESSOR_ATTEMPT_REFERENCE,
        "successor_verification_attempt_digest": SUCCESSOR_DIGEST,
        "successor_verification_attempt_released_at": CUTOVER,
    }
    values.update(overrides)
    return values


def _resolve(
    *, read_port: object, **overrides: object
) -> ValidationResultNonVerifiabilitySupersessionV2AuthorityView:
    """Resolve canonical caller-known coordinates with optional hostile overrides."""
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "result_reference": RESULT_REFERENCE,
        "result_digest": RESULT_DIGEST,
        "failed_evidence_kind": "analysis_weight_receipt",
        "verification_attempt_reference": ATTEMPT_REFERENCE,
        "verification_attempt_digest": ATTEMPT_DIGEST,
        "evidence_version": 2,
        "owner_contract_reference": OWNER_REFERENCE,
        "owner_contract_version": 7,
        "owner_contract_digest": OWNER_DIGEST,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_validation_result_nonverifiability_supersession_v2_authority(**values)


def test_current_non_reproducible_outcome_resolves_with_exact_failed_artifact() -> None:
    """Expose predecessor provenance while keeping correction coordinates private."""
    record = _record()
    port = _ReadPort(record)
    view = _resolve(read_port=port)

    assert isinstance(port, ValidationResultNonVerifiabilitySupersessionV2AuthorityReadPort)
    assert record.predecessor.failure_mode == "non_reproducible"
    assert record.evidence_version == 2
    assert record.released_at == RELEASED_AT
    assert record.superseded_at is None
    assert record.successor_fields is None
    assert port.calls == [
        {
            "tenant_record_id": TENANT,
            "validity_study_id": STUDY,
            "result_reference": RESULT_REFERENCE,
            "result_digest": RESULT_DIGEST,
            "failed_evidence_kind": "analysis_weight_receipt",
            "verification_attempt_reference": ATTEMPT_REFERENCE,
            "verification_attempt_digest": ATTEMPT_DIGEST,
            "evidence_version": 2,
            "owner_contract_reference": OWNER_REFERENCE,
            "owner_contract_version": 7,
            "owner_contract_digest": OWNER_DIGEST,
        }
    ]
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    fields = dict(view.fields)
    assert fields["failure_mode"] == "non_reproducible"
    assert fields["failed_evidence_reference"] == FAILED_REFERENCE
    assert fields["failed_evidence_digest"] == FAILED_DIGEST
    assert fields["failed_evidence_released_at"] == FAILED_RELEASED_AT
    assert fields["verification_attempt_released_at"] == ATTEMPT_RELEASED_AT
    assert fields["evidence_version"] == 2
    assert fields["released_at"] == RELEASED_AT
    assert "superseded_at" not in fields
    assert "successor_target_failed_evidence_reference" not in fields
    assert "successor_verification_attempt_reference" not in fields


def test_exact_artifact_successor_preserves_historical_use_but_ends_at_cutover() -> None:
    """Require one atomic same-result, same-artifact successor attempt."""
    record = _record(**_successor_overrides())
    assert dict(record.successor_fields or ()) == {
        "successor_failed_evidence_kind": "analysis_weight_receipt",
        "successor_target_failed_evidence_digest": FAILED_DIGEST,
        "successor_target_failed_evidence_reference": FAILED_REFERENCE,
        "successor_target_failed_evidence_released_at": FAILED_RELEASED_AT,
        "successor_target_result_digest": RESULT_DIGEST,
        "successor_target_result_reference": RESULT_REFERENCE,
        "successor_verification_attempt_digest": SUCCESSOR_DIGEST,
        "successor_verification_attempt_reference": SUCCESSOR_ATTEMPT_REFERENCE,
        "successor_verification_attempt_released_at": CUTOVER,
    }
    view = _resolve(read_port=_ReadPort(record), used_at=CUTOVER - timedelta(seconds=1))
    assert dict(view.fields)["result_reference"] == RESULT_REFERENCE
    with pytest.raises(ValidationResultNonVerifiabilitySupersessionV2AuthorityIntegrityError):
        _resolve(read_port=_ReadPort(record), used_at=CUTOVER)


def test_authorization_denial_happens_before_owner_resolution() -> None:
    """Keep purpose denial ahead of owner evidence lookup."""
    port = _ReadPort(_record())
    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))
    assert port.calls == []


def test_missing_or_noncanonical_owner_evidence_fails_closed() -> None:
    """Reject absence and foreign record types after authorization."""
    with pytest.raises(ValidationResultNonVerifiabilitySupersessionV2AuthorityNotFound):
        _resolve(read_port=_ReadPort(None))
    with pytest.raises(ValidationResultNonVerifiabilitySupersessionV2AuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))


@pytest.mark.parametrize(
    "predecessor_overrides",
    [
        {"tenant_record_id": OTHER_TENANT},
        {"validity_study_id": OTHER_STUDY},
        {"result_reference": OTHER_RESULT_REFERENCE},
        {"result_digest": "a" * 64},
        {
            "failed_evidence_kind": "variance_design_receipt",
            "failed_evidence_reference": (
                "variance_design_receipt:22222222-2222-4222-8222-222222222222"
            ),
        },
        {"verification_attempt_reference": OTHER_ATTEMPT_REFERENCE},
        {"verification_attempt_digest": "c" * 64},
        {"owner_contract_reference": OTHER_OWNER_REFERENCE},
        {"owner_contract_version": 8},
        {"owner_contract_digest": "d" * 64},
    ],
)
def test_owner_evidence_must_match_every_caller_known_coordinate(
    predecessor_overrides: dict[str, object]
) -> None:
    """Reject evidence selected by an incomplete or different lookup tuple."""
    record = _record(predecessor=_predecessor(**predecessor_overrides))
    with pytest.raises(ValidationResultNonVerifiabilitySupersessionV2AuthorityIntegrityError):
        _resolve(read_port=_ReadPort(record))


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
        ("result_reference", "wrong:result", ValueError),
        ("result_digest", "ABC", ValueError),
        ("failed_evidence_kind", "unknown", ValueError),
        ("verification_attempt_reference", "wrong:attempt", ValueError),
        ("verification_attempt_digest", "3" * 63, ValueError),
        ("evidence_version", False, ValueError),
        ("evidence_version", 1, ValueError),
        ("owner_contract_reference", "wrong:contract", ValueError),
        ("owner_contract_version", 0, ValueError),
        ("owner_contract_digest", "5" * 63, ValueError),
        ("used_at", datetime(2026, 9, 17, 6, 10), ValueError),
        ("purpose_code", "Selection Validity Analysis", ValueError),
    ],
)
def test_invalid_request_or_dependency_fails_before_owner_resolution(
    key: str, value: object, error: type[Exception]
) -> None:
    """Validate caller/dependency shapes before any owner read."""
    port: object = _ReadPort(_record())
    overrides = {key: value}
    if key == "read_port":
        port = value
        overrides = {}
    with pytest.raises(error):
        _resolve(read_port=port, **overrides)
    if isinstance(port, _ReadPort):
        assert port.calls == []


def test_pre_release_use_fails_closed() -> None:
    """Do not expose a predecessor before its released authority instant."""
    with pytest.raises(ValidationResultNonVerifiabilitySupersessionV2AuthorityIntegrityError):
        _resolve(
            read_port=_ReadPort(_record()),
            used_at=RELEASED_AT - timedelta(seconds=1),
        )


def test_record_requires_exact_non_reproducible_predecessor_and_v2() -> None:
    """Keep v2 reserved for exact ordinary non-reproducible owner evidence."""
    with pytest.raises(TypeError, match="exact ValidationResultNonVerifiabilityRecord"):
        ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord(
            predecessor=object(), evidence_version=2
        )
    with pytest.raises(ValueError, match="reserved for non_reproducible"):
        _record(
            predecessor=_predecessor(
                failure_mode="missing",
                failed_evidence_reference=None,
                failed_evidence_digest=None,
                failed_evidence_released_at=None,
            )
        )
    with pytest.raises(ValueError, match="evidence_version must be 2"):
        _record(evidence_version=1)
    with pytest.raises(TypeError, match="issued only by"):
        ValidationResultNonVerifiabilitySupersessionV2AuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )


def test_incomplete_successor_tuple_fails_closed() -> None:
    """Never accept a cutover without every exact-artifact successor coordinate."""
    values = _successor_overrides()
    values["successor_target_failed_evidence_digest"] = None
    with pytest.raises(ValueError, match="requires cutover"):
        _record(**values)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"superseded_at": RELEASED_AT}, "later than predecessor release"),
        ({"successor_target_result_reference": OTHER_RESULT_REFERENCE}, "exact predecessor result"),
        ({"successor_target_result_digest": "a" * 64}, "exact predecessor result"),
        ({"successor_failed_evidence_kind": "variance_design_receipt"}, "same failed-evidence family"),
        ({"successor_target_failed_evidence_reference": OTHER_FAILED_REFERENCE}, "exact failed artifact"),
        ({"successor_target_failed_evidence_digest": "b" * 64}, "exact failed artifact"),
        (
            {"successor_target_failed_evidence_released_at": FAILED_RELEASED_AT + timedelta(seconds=1)},
            "exact failed artifact",
        ),
        ({"successor_verification_attempt_reference": ATTEMPT_REFERENCE}, "new reference"),
        ({"successor_verification_attempt_digest": RESULT_DIGEST}, "identify new evidence"),
        ({"successor_verification_attempt_digest": FAILED_DIGEST}, "identify new evidence"),
        ({"successor_verification_attempt_digest": ATTEMPT_DIGEST}, "identify new evidence"),
        ({"successor_verification_attempt_digest": OWNER_DIGEST}, "identify new evidence"),
        (
            {"successor_verification_attempt_released_at": CUTOVER + timedelta(seconds=1)},
            "released exactly at supersession",
        ),
    ],
)
def test_successor_must_bind_exact_predecessor_artifact(
    override: dict[str, object], message: str
) -> None:
    """Reject another result, artifact, family, reused attempt, alias, or split cutover."""
    with pytest.raises(ValueError, match=message):
        _record(**_successor_overrides(**override))


@pytest.mark.parametrize(
    "override",
    [
        {"superseded_at": datetime(2026, 9, 17, 7, 0)},
        {"successor_target_result_reference": "wrong:result"},
        {"successor_target_result_digest": "x"},
        {"successor_failed_evidence_kind": "unknown"},
        {"successor_target_failed_evidence_reference": "wrong:artifact"},
        {"successor_target_failed_evidence_digest": "x"},
        {"successor_target_failed_evidence_released_at": datetime(2026, 9, 17, 5, 59)},
        {"successor_verification_attempt_reference": "wrong:attempt"},
        {"successor_verification_attempt_digest": "x"},
        {"successor_verification_attempt_released_at": datetime(2026, 9, 17, 7, 0)},
    ],
)
def test_malformed_successor_coordinates_fail_closed(
    override: dict[str, object]
) -> None:
    """Reject malformed references, digests and naive chronology before correction use."""
    with pytest.raises(ValueError):
        _record(**_successor_overrides(**override))


def test_record_and_view_are_structurally_immutable_and_uuid_views_are_detached() -> None:
    """Prevent retained aliases or attribute writes from mutating accepted authority."""
    tenant = UUID(str(TENANT))
    predecessor = _predecessor(tenant_record_id=tenant)
    record = _record(predecessor=predecessor)
    object.__setattr__(tenant, "int", OTHER_TENANT.int)
    assert record.predecessor.tenant_record_id == TENANT
    assert dict(record.fields)["failed_evidence_reference"] == FAILED_REFERENCE
    with pytest.raises(AttributeError):
        object.__setattr__(record, "evidence_version", 3)

    view = _resolve(read_port=_ReadPort(record))
    returned_tenant = view.tenant_record_id
    object.__setattr__(returned_tenant, "int", OTHER_TENANT.int)
    assert view.tenant_record_id == TENANT
    with pytest.raises(AttributeError):
        object.__setattr__(view, "fields", ())


def test_v2_rejects_structurally_forged_non_reproducible_predecessor() -> None:
    """Revalidate exact failed-artifact presence even if tuple construction bypasses v1 guards."""
    predecessor = _predecessor()
    forged_values = list(predecessor)
    forged_values[6] = None
    forged = tuple.__new__(ValidationResultNonVerifiabilityRecord, forged_values)
    with pytest.raises(ValueError, match="retain exact failed-artifact evidence"):
        _record(predecessor=forged)
