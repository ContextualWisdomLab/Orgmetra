"""Persistence-facing audit envelope regression tests."""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID

from orgmetra_hris_kernel.audit import AuditOutboxEvent


def test_canonical_json_is_the_exact_byte_contract_for_persistent_digest():
    """The database can store and re-hash exactly the producer's canonical bytes."""
    event = AuditOutboxEvent(
        event_id=UUID("00000000-0000-7000-8000-000000000103"),
        tenant_record_id=UUID("10000000-0000-7000-8000-000000000001"),
        source_service="people_core",
        event_type="orgmetra.people.candidate.recorded",
        resource_reference="candidate_profile:01JTESTOPAQUE",
        actor_reference="keyverse_subject:01JACTOROPAQUE",
        purpose_code="talent_acquisition",
        reason_code="candidate_created",
        evidence_version_code="candidate-create:v1",
        result_code="recorded",
        occurred_at=datetime(2026, 8, 17, 2, 30, tzinfo=timezone.utc),
        high_impact=False,
    )

    expected = (
        '{"data":{"high_impact":false,"result_code":"recorded"},'
        '"datacontenttype":"application/json",'
        '"id":"00000000-0000-7000-8000-000000000103",'
        '"orgmetraactor":"keyverse_subject:01JACTOROPAQUE",'
        '"orgmetraevidence":"candidate-create:v1",'
        '"orgmetrapurpose":"talent_acquisition",'
        '"orgmetrareason":"candidate_created",'
        '"orgmetratenant":"10000000-0000-7000-8000-000000000001",'
        '"source":"urn:orgmetra:people_core","specversion":"1.0",'
        '"subject":"candidate_profile:01JTESTOPAQUE",'
        '"time":"2026-08-17T02:30:00Z",'
        '"type":"orgmetra.people.candidate.recorded"}'
    )

    assert event.canonical_json() == expected
    assert event.content_digest() == sha256(expected.encode("utf-8")).hexdigest()
