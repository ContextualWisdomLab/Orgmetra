"""Executable contract for value-minimized HR document-record evidence."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid1, uuid4

import pytest

from orgmetra_document_record_evidence import build_document_record_evidence


def values() -> dict[str, object]:
    """Return one valid caller-owned document-record input set."""
    now = datetime.now(timezone.utc)
    return {
        "tenant_record_id": str(uuid4()),
        "person_record_reference": f"person_record:{uuid4()}",
        "employment_record_reference": f"employment_record:{uuid4()}",
        "uploader_actor_reference": f"actor:{uuid4()}",
        "document_category_code": "employment_contract",
        "artifact_reference": f"document_artifact:{uuid4()}",
        "artifact_digest": "a" * 64,
        "source_provenance_digest": "b" * 64,
        "retention_policy_reference": f"retention_policy:{uuid4()}",
        "retention_policy_digest": "c" * 64,
        "received_at": now - timedelta(seconds=1),
    }


def test_builds_value_minimized_document_evidence() -> None:
    """Build one canonical record without copying document content or HR values."""
    evidence = build_document_record_evidence(**values())
    document = evidence.canonical_document()
    assert document["schema_version"] == "orgmetra.document_record_evidence.v1"
    assert document["classification_code"] == "restricted_hr"
    assert document["content_storage_state"] == "artifact_reference_only"
    assert document["decision_authority_state"] == "not_authorized_for_employment_decision"
    assert document["document_category_code"] == "employment_contract"
    assert document["artifact_digest"] == "a" * 64
    assert document["source_provenance_digest"] == "b" * 64
    assert "document_content" not in document
    assert "document_title" not in document
    assert len(evidence.sha256_digest()) == 64
    assert evidence.canonical_json() == evidence.canonical_json()
    assert repr(evidence) == "DocumentRecordEvidence(<redacted>)"


def test_generates_packet_owned_reference_and_system_time() -> None:
    """Generate packet identity and recorded time inside the Orgmetra issuance boundary."""
    before = datetime.now(timezone.utc)
    evidence = build_document_record_evidence(**values())
    after = datetime.now(timezone.utc)
    reference = evidence.document_record_reference
    assert reference.startswith("document_record:")
    assert UUID(reference.split(":", 1)[1]).version == 4
    assert before <= evidence.recorded_at <= after
    assert evidence.recorded_at.tzinfo is timezone.utc


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("tenant_record_id", 7),
        ("tenant_record_id", "not-a-uuid"),
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000"),
        ("person_record_reference", 7),
        ("person_record_reference", f"wrong_namespace:{uuid4()}"),
        ("person_record_reference", f"person_record:{uuid1()}"),
        ("person_record_reference", "person_record:"),
        ("employment_record_reference", "employment_record:"),
        ("uploader_actor_reference", "actor:Jane-Doe"),
        ("document_category_code", 7),
        ("document_category_code", "free_form_category"),
        ("artifact_reference", "document_artifact:"),
        ("artifact_digest", "A" * 64),
        ("source_provenance_digest", "b" * 63),
        ("retention_policy_reference", "retention_policy:"),
        ("retention_policy_digest", "not-a-digest"),
    ],
)
def test_rejects_malformed_trust_evidence(field_name: str, bad_value: object) -> None:
    """Fail closed before malformed trust evidence can enter canonical audit correlation."""
    payload = values()
    payload[field_name] = bad_value
    with pytest.raises(ValueError):
        build_document_record_evidence(**payload)


def test_rejects_future_received_time() -> None:
    """Do not record a document as received after its system issuance time."""
    payload = values()
    payload["received_at"] = datetime.now(timezone.utc) + timedelta(days=1)
    with pytest.raises(ValueError, match="received_at cannot be in the future"):
        build_document_record_evidence(**payload)


def test_rejects_non_utc_received_time() -> None:
    """Require detached built-in UTC business-event time at the evidence boundary."""
    payload = values()
    payload["received_at"] = datetime.now().replace(tzinfo=None)
    with pytest.raises(ValueError, match="received_at must be an exact built-in UTC datetime"):
        build_document_record_evidence(**payload)


def test_rejects_valid_value_rewrite_after_issuance() -> None:
    """Do not emit a second evidence truth after a frozen packet is forcibly rewritten."""
    evidence = build_document_record_evidence(**values())
    object.__setattr__(evidence, "document_category_code", "policy_acknowledgement")
    with pytest.raises(ValueError, match="document record evidence changed after construction"):
        evidence.canonical_json()
