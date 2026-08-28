"""Privacy regressions for read-time audit-envelope integrity verification."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import UUID

import pytest

from orgmetra_audit_evidence_review import PersistedAuditEvidenceRow

TENANT = UUID("10000000-0000-7000-8000-000000000001")
EVENT = UUID("11111111-1111-4111-8111-111111111111")
RECORDED = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)


def _document() -> dict[str, object]:
    """Return the exact existing PII-minimized audit envelope shape."""
    return {
        "data": {"high_impact": False, "result_code": "updated"},
        "datacontenttype": "application/json",
        "id": str(EVENT),
        "orgmetraactor": "actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "orgmetraevidence": "v1",
        "orgmetrapurpose": "people_record_update",
        "orgmetrareason": "authorized_change",
        "orgmetratenant": str(TENANT),
        "source": "urn:orgmetra:people_api",
        "specversion": "1.0",
        "subject": "person:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "time": "2026-08-20T11:59:00Z",
        "type": "orgmetra.people.updated",
    }


def _row(canonical: str) -> PersistedAuditEvidenceRow:
    """Build a row whose digest matches the supplied bytes exactly."""
    return PersistedAuditEvidenceRow(
        tenant_record_id=TENANT,
        audit_event_record_id=EVENT,
        canonical_event_json=canonical,
        event_envelope_digest=sha256(canonical.encode("utf-8")).hexdigest(),
        recorded_at=RECORDED,
    )


def test_read_time_verification_accepts_governed_optional_confirmation_extension() -> None:
    """High-impact evidence may carry the single existing confirmation extension."""
    document = _document()
    document["data"] = {"high_impact": True, "result_code": "confirmed"}
    document["orgmetraconfirmation"] = "confirmation:dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    canonical = json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    assert _row(canonical).canonical_event_json == canonical


def test_read_time_verification_rejects_extra_top_level_hr_payload() -> None:
    """A recomputed digest cannot legitimize a widened envelope carrying HR payload."""
    document = _document()
    document["employee_name"] = "should-never-enter-audit-envelope"
    canonical = json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    with pytest.raises(ValueError, match="governed audit envelope shape"):
        _row(canonical)


def test_read_time_verification_rejects_extra_data_payload() -> None:
    """The nested data object stays limited to result and high-impact metadata."""
    document = _document()
    data = document["data"]
    assert isinstance(data, dict)
    data["rating"] = 5
    canonical = json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    with pytest.raises(ValueError, match="governed audit data shape"):
        _row(canonical)


def test_read_time_verification_rejects_non_object_data_payload() -> None:
    """The audit `data` member must remain the governed metadata object, not another JSON type."""
    document = _document()
    document["data"] = []
    canonical = json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    with pytest.raises(ValueError, match="governed audit data shape"):
        _row(canonical)


@pytest.mark.parametrize(
    "data",
    [
        {"high_impact": 1, "result_code": "updated"},
        {"high_impact": False, "result_code": 7},
    ],
)
def test_read_time_verification_rejects_noncanonical_data_value_types(
    data: dict[str, object],
) -> None:
    """The governed audit data values remain an exact boolean and result-code string."""
    document = _document()
    document["data"] = data
    canonical = json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    with pytest.raises(ValueError, match="governed audit value types"):
        _row(canonical)


def test_read_time_verification_rejects_nonfinite_json_numbers() -> None:
    """JSON NaN and Infinity extensions cannot enter canonical evidence."""
    document = _document()
    document["data"] = {"high_impact": False, "result_code": float("nan")}
    canonical = json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    with pytest.raises(ValueError, match="valid UTF-8 JSON"):
        _row(canonical)


@pytest.mark.parametrize(
    ("member", "value"),
    [("source", 7), ("orgmetraconfirmation", 7)],
)
def test_read_time_verification_rejects_noncanonical_event_value_types(
    member: str, value: object,
) -> None:
    """CloudEvents members and optional confirmation remain exact strings."""
    document = _document()
    document[member] = value
    canonical = json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    with pytest.raises(ValueError, match="governed audit value types"):
        _row(canonical)


def test_unencodable_text_fails_closed_as_validation_error() -> None:
    """Malformed caller text does not escape as an implementation encoding exception."""
    malformed = '{"bad":"' + chr(0xD800) + '"}'
    with pytest.raises(ValueError, match="valid UTF-8 text"):
        PersistedAuditEvidenceRow(
            tenant_record_id=TENANT,
            audit_event_record_id=EVENT,
            canonical_event_json=malformed,
            event_envelope_digest="0" * 64,
            recorded_at=RECORDED,
        )
