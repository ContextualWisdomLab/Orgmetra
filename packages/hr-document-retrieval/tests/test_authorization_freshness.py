"""Regression for authorization expiry during protected artifact retrieval."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import pytest

import orgmetra_hr_document_retrieval.retrieval as retrieval_module
from orgmetra_hr_document_retrieval import (
    DocumentArtifact,
    DocumentRetrievalAuthorization,
    DocumentRetrievalQuery,
    DocumentRetrievalScope,
    HrDocumentRetrievalError,
    retrieve_hr_document,
)


def test_authorization_expiring_during_artifact_read_blocks_audit_and_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Authorization must still be current after the protected storage operation."""
    initial = datetime(2026, 8, 25, 14, 0, tzinfo=timezone.utc)
    after_read = initial + timedelta(minutes=2)
    clock = iter((initial, after_read))
    monkeypatch.setattr(retrieval_module, "_now_utc", lambda: next(clock))

    tenant = str(uuid4())
    document = f"document_record:{uuid4()}"
    person = f"person_record:{uuid4()}"
    employment = f"employment_record:{uuid4()}"
    artifact_reference = f"document_artifact:{uuid4()}"
    requester = f"actor:{uuid4()}"
    reviewer = f"actor:{uuid4()}"
    content = b"sensitive-document"
    digest = sha256(content).hexdigest()

    request = DocumentRetrievalQuery(
        tenant_record_id=tenant,
        document_record_reference=document,
        requester_reference=requester,
        purpose_code="employee_file_review",
        reason_code="authorized_hr_case",
        max_bytes=1024,
    )
    resolved = DocumentRetrievalScope(
        tenant_record_id=tenant,
        document_record_reference=document,
        person_record_reference=person,
        employment_record_reference=employment,
        artifact_reference=artifact_reference,
        artifact_digest_sha256=digest,
        media_type="application/pdf",
        retention_state="retained_record",
        classification_code="restricted_hr",
    )
    decision = DocumentRetrievalAuthorization(
        tenant_record_id=tenant,
        document_record_reference=document,
        person_record_reference=person,
        employment_record_reference=employment,
        artifact_reference=artifact_reference,
        artifact_digest_sha256=digest,
        retention_state="retained_record",
        classification_code="restricted_hr",
        authorized_max_bytes=1024,
        delivery_context_code="authenticated_hr_session",
        requester_reference=requester,
        reviewer_reference=reviewer,
        purpose_code="employee_file_review",
        reason_code="authorized_hr_case",
        authorization_evidence_digest_sha256="a" * 64,
        reviewed_at=initial - timedelta(minutes=1),
        expires_at=initial + timedelta(minutes=1),
        permitted=True,
    )
    calls: list[str] = []

    class Resolver:
        def resolve_document_scope(self, query: DocumentRetrievalQuery) -> DocumentRetrievalScope:
            calls.append("scope")
            return resolved

    class Authority:
        def authorize_document_retrieval(
            self,
            query: DocumentRetrievalQuery,
            scope: DocumentRetrievalScope,
        ) -> DocumentRetrievalAuthorization:
            calls.append("authority")
            return decision

    class Reader:
        def read_document_artifact(self, artifact: str, max_bytes: int) -> DocumentArtifact:
            calls.append("artifact")
            return DocumentArtifact(content=content, digest_sha256=digest)

    class Audit:
        def append_document_retrieval_receipt(self, canonical_receipt_json: str) -> None:
            calls.append("audit")

    with pytest.raises(HrDocumentRetrievalError, match="expired before byte release"):
        retrieve_hr_document(
            query=request,
            metadata_resolver=Resolver(),
            authority=Authority(),
            artifact_reader=Reader(),
            audit_writer=Audit(),
        )

    assert calls == ["scope", "authority", "artifact"]
