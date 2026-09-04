from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from uuid import UUID, uuid4

import pytest

import orgmetra_hr_document_retrieval.retrieval as retrieval_module
from orgmetra_hr_document_retrieval import (
    DocumentArtifact,
    DocumentRetrievalAuthorization,
    DocumentRetrievalQuery,
    DocumentRetrievalResult,
    DocumentRetrievalScope,
    HrDocumentRetrievalError,
    retrieve_hr_document,
)

NOW = datetime.now(timezone.utc)
CONTENT = b"governed-hr-document"
CONTENT_DIGEST = sha256(CONTENT).hexdigest()
TENANT = str(uuid4())
DOCUMENT = f"document_record:{uuid4()}"
PERSON = f"person_record:{uuid4()}"
EMPLOYMENT = f"employment_record:{uuid4()}"
ARTIFACT = f"document_artifact:{uuid4()}"
REQUESTER = f"actor:{uuid4()}"
REVIEWER = f"actor:{uuid4()}"
AUTH_DIGEST = "a" * 64


def query(**changes: object) -> DocumentRetrievalQuery:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "document_record_reference": DOCUMENT,
        "requester_reference": REQUESTER,
        "purpose_code": "employee_file_review",
        "reason_code": "authorized_hr_case",
        "max_bytes": 1024,
    }
    values.update(changes)
    return DocumentRetrievalQuery(**values)  # type: ignore[arg-type]


def scope(**changes: object) -> DocumentRetrievalScope:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "document_record_reference": DOCUMENT,
        "person_record_reference": PERSON,
        "employment_record_reference": EMPLOYMENT,
        "artifact_reference": ARTIFACT,
        "artifact_digest_sha256": CONTENT_DIGEST,
        "media_type": "application/pdf",
        "retention_state": "retained_record",
        "classification_code": "restricted_hr",
    }
    values.update(changes)
    return DocumentRetrievalScope(**values)  # type: ignore[arg-type]


def authorization(**changes: object) -> DocumentRetrievalAuthorization:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "document_record_reference": DOCUMENT,
        "person_record_reference": PERSON,
        "employment_record_reference": EMPLOYMENT,
        "artifact_reference": ARTIFACT,
        "artifact_digest_sha256": CONTENT_DIGEST,
        "retention_state": "retained_record",
        "classification_code": "restricted_hr",
        "authorized_max_bytes": 1024,
        "delivery_context_code": "authenticated_hr_session",
        "requester_reference": REQUESTER,
        "reviewer_reference": REVIEWER,
        "purpose_code": "employee_file_review",
        "reason_code": "authorized_hr_case",
        "authorization_evidence_digest_sha256": AUTH_DIGEST,
        "reviewed_at": NOW - timedelta(minutes=5),
        "expires_at": NOW + timedelta(minutes=5),
        "permitted": True,
    }
    values.update(changes)
    return DocumentRetrievalAuthorization(**values)  # type: ignore[arg-type]


class Resolver:
    def __init__(self, value: object | None = None, calls: list[str] | None = None) -> None:
        self.value = scope() if value is None else value
        self.calls = calls if calls is not None else []

    def resolve_document_scope(self, request: DocumentRetrievalQuery) -> object:
        self.calls.append("scope")
        assert request.document_record_reference == DOCUMENT
        return self.value


class Authority:
    def __init__(self, value: object | None = None, calls: list[str] | None = None) -> None:
        self.value = authorization() if value is None else value
        self.calls = calls if calls is not None else []

    def authorize_document_retrieval(
        self,
        request: DocumentRetrievalQuery,
        resolved: DocumentRetrievalScope,
    ) -> object:
        self.calls.append("authority")
        assert request.tenant_record_id == resolved.tenant_record_id
        return self.value


class Reader:
    def __init__(self, value: object | None = None, calls: list[str] | None = None) -> None:
        self.value = DocumentArtifact(CONTENT, CONTENT_DIGEST) if value is None else value
        self.calls = calls if calls is not None else []

    def read_document_artifact(self, artifact_reference: str, max_bytes: int) -> object:
        self.calls.append("artifact")
        assert artifact_reference == ARTIFACT
        assert max_bytes == 1024
        return self.value


class Audit:
    def __init__(
        self,
        calls: list[str] | None = None,
        failure: Exception | None = None,
    ) -> None:
        self.calls = calls if calls is not None else []
        self.failure = failure
        self.receipts: list[str] = []

    def append_document_retrieval_receipt(self, canonical_receipt_json: str) -> None:
        self.calls.append("audit")
        if self.failure is not None:
            raise self.failure
        self.receipts.append(canonical_receipt_json)


def execute(
    *,
    q: DocumentRetrievalQuery | None = None,
    resolver: object | None = None,
    auth: object | None = None,
    reader: object | None = None,
    audit: object | None = None,
) -> DocumentRetrievalResult:
    return retrieve_hr_document(
        query=q or query(),
        metadata_resolver=resolver or Resolver(),  # type: ignore[arg-type]
        authority=auth or Authority(),  # type: ignore[arg-type]
        artifact_reader=reader or Reader(),  # type: ignore[arg-type]
        audit_writer=audit or Audit(),  # type: ignore[arg-type]
    )


def test_happy_path_authorizes_verifies_audits_then_releases_bytes() -> None:
    calls: list[str] = []
    audit = Audit(calls)
    result = execute(
        resolver=Resolver(calls=calls),
        auth=Authority(calls=calls),
        reader=Reader(calls=calls),
        audit=audit,
    )
    assert calls == ["scope", "authority", "artifact", "audit"]
    assert result.content == CONTENT
    assert result.media_type == "application/pdf"
    assert result.retrieval_state == "retrieved_after_authorization_and_audit"
    assert result.decision_authority_state == "not_authorized_for_employment_decision"
    assert len(audit.receipts) == 1
    payload = json.loads(audit.receipts[0])
    assert payload["tenant_record_id"] == TENANT
    assert payload["person_record_reference"] == PERSON
    assert payload["employment_record_reference"] == EMPLOYMENT
    assert payload["purpose_code"] == "employee_file_review"
    assert payload["reason_code"] == "authorized_hr_case"
    assert payload["byte_count"] == len(CONTENT)
    assert payload["delivery_context_code"] == "authenticated_hr_session"
    assert payload["artifact_digest_sha256"] == CONTENT_DIGEST
    assert payload["schema_version"] == "orgmetra.hr_document_retrieval_receipt.v1"
    assert result.receipt_digest_sha256 == sha256(audit.receipts[0].encode()).hexdigest()
    assert "governed-hr-document" not in audit.receipts[0]


def test_denied_or_mismatched_authorization_never_reads_bytes() -> None:
    calls: list[str] = []
    with pytest.raises(HrDocumentRetrievalError, match="not authorized"):
        execute(
            auth=Authority(authorization(permitted=False), calls),
            reader=Reader(calls=calls),
            audit=Audit(calls),
        )
    assert "artifact" not in calls and "audit" not in calls

    calls = []
    wrong = replace(authorization(), purpose_code="different_review_purpose")
    with pytest.raises(HrDocumentRetrievalError, match="exact retrieval scope"):
        execute(auth=Authority(wrong, calls), reader=Reader(calls=calls), audit=Audit(calls))
    assert "artifact" not in calls and "audit" not in calls

    wrong_artifact = replace(authorization(), artifact_digest_sha256="b" * 64)
    with pytest.raises(HrDocumentRetrievalError, match="exact retrieval scope"):
        execute(auth=Authority(wrong_artifact))


def test_scope_mismatch_stops_before_authority() -> None:
    calls: list[str] = []
    other = replace(scope(), document_record_reference=f"document_record:{uuid4()}")
    with pytest.raises(HrDocumentRetrievalError, match="requested tenant/document scope"):
        execute(
            resolver=Resolver(other, calls),
            auth=Authority(calls=calls),
            reader=Reader(calls=calls),
            audit=Audit(calls),
        )
    assert calls == ["scope"]


def test_artifact_digest_and_size_fail_before_audit() -> None:
    calls: list[str] = []
    corrupt = DocumentArtifact(b"different", sha256(b"different").hexdigest())
    with pytest.raises(HrDocumentRetrievalError, match="digest does not match"):
        execute(reader=Reader(corrupt, calls), audit=Audit(calls))
    assert "audit" not in calls

    calls = []
    oversized = DocumentArtifact(b"x" * 2048, sha256(b"x" * 2048).hexdigest())
    with pytest.raises(HrDocumentRetrievalError, match="authorized byte limit"):
        execute(reader=Reader(oversized, calls), audit=Audit(calls))
    assert "audit" not in calls


def test_audit_failure_blocks_byte_release() -> None:
    with pytest.raises(OSError, match="audit unavailable"):
        execute(audit=Audit(failure=OSError("audit unavailable")))


def test_authorization_expiring_during_audit_blocks_byte_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A slow audit append cannot release bytes after authorization expires."""
    clock = iter(
        (
            NOW,
            NOW + timedelta(minutes=1),
            NOW + timedelta(minutes=10),
        )
    )
    monkeypatch.setattr(retrieval_module, "_now_utc", lambda: next(clock))
    calls: list[str] = []

    with pytest.raises(HrDocumentRetrievalError, match="expired before byte release"):
        execute(reader=Reader(calls=calls), audit=Audit(calls))

    assert calls == ["artifact", "audit"]


def test_expired_future_or_actor_colliding_authorization_fails_closed() -> None:
    with pytest.raises(HrDocumentRetrievalError, match="expired or chronologically invalid"):
        execute(auth=Authority(authorization(expires_at=NOW)))
    with pytest.raises(HrDocumentRetrievalError, match="later than the retrieval instant"):
        execute(
            auth=Authority(
                authorization(
                    reviewed_at=NOW + timedelta(minutes=2),
                    expires_at=NOW + timedelta(minutes=5),
                )
            )
        )
    with pytest.raises(HrDocumentRetrievalError, match="different accountable actor"):
        authorization(reviewer_reference=REQUESTER)


def test_retention_classification_media_and_policy_codes_fail_closed() -> None:
    with pytest.raises(HrDocumentRetrievalError, match="retention_state"):
        scope(retention_state="disposed_record")
    with pytest.raises(HrDocumentRetrievalError, match="classification_code"):
        scope(classification_code="public_record")
    with pytest.raises(HrDocumentRetrievalError, match="media_type"):
        scope(media_type="application/pdf; charset=utf-8")
    with pytest.raises(HrDocumentRetrievalError, match="purpose_code"):
        query(purpose_code="free form")
    with pytest.raises(HrDocumentRetrievalError, match="reason_code"):
        query(reason_code="x")
    with pytest.raises(HrDocumentRetrievalError, match="authorized_max_bytes"):
        authorization(authorized_max_bytes=0)
    with pytest.raises(HrDocumentRetrievalError, match="delivery_context_code"):
        authorization(delivery_context_code="public_download")


def test_exact_runtime_primitives_reject_subclass_and_bool_int_confusion() -> None:
    class ForgedText(str):
        pass

    with pytest.raises(HrDocumentRetrievalError, match="tenant_record_id"):
        query(tenant_record_id=ForgedText(TENANT))
    with pytest.raises(HrDocumentRetrievalError, match="max_bytes"):
        query(max_bytes=True)
    with pytest.raises(HrDocumentRetrievalError, match="permitted"):
        auth = authorization()
        object.__setattr__(auth, "permitted", 1)
        execute(auth=Authority(auth))


def test_query_mutation_is_revalidated_before_protected_resolution() -> None:
    calls: list[str] = []
    q = query()
    object.__setattr__(q, "max_bytes", 0)
    with pytest.raises(HrDocumentRetrievalError, match="max_bytes"):
        execute(q=q, resolver=Resolver(calls=calls))
    assert calls == []


def test_resolver_authority_and_artifact_outputs_are_revalidated_after_mutation() -> None:
    mutated_scope = scope()
    object.__setattr__(mutated_scope, "classification_code", "public_record")
    with pytest.raises(HrDocumentRetrievalError, match="classification_code"):
        execute(resolver=Resolver(mutated_scope))

    mutated_auth = authorization()
    object.__setattr__(mutated_auth, "authorization_evidence_digest_sha256", "BAD")
    with pytest.raises(HrDocumentRetrievalError, match="authorization_evidence_digest_sha256"):
        execute(auth=Authority(mutated_auth))

    mutated_artifact = DocumentArtifact(CONTENT, CONTENT_DIGEST)
    object.__setattr__(mutated_artifact, "content", bytearray(CONTENT))
    with pytest.raises(HrDocumentRetrievalError, match="built-in bytes"):
        execute(reader=Reader(mutated_artifact))


def test_callbacks_cannot_widen_the_authoritative_byte_limit() -> None:
    observed: list[int] = []

    class MutatingResolver:
        def resolve_document_scope(self, request: DocumentRetrievalQuery) -> DocumentRetrievalScope:
            object.__setattr__(request, "max_bytes", 2048)
            return scope()

    class EchoingAuthority:
        def authorize_document_retrieval(
            self,
            request: DocumentRetrievalQuery,
            resolved: DocumentRetrievalScope,
        ) -> DocumentRetrievalAuthorization:
            assert resolved.artifact_reference == ARTIFACT
            return authorization(authorized_max_bytes=request.max_bytes)

    class RecordingReader:
        def read_document_artifact(self, artifact_reference: str, max_bytes: int) -> DocumentArtifact:
            assert artifact_reference == ARTIFACT
            observed.append(max_bytes)
            return DocumentArtifact(CONTENT, CONTENT_DIGEST)

    execute(
        resolver=MutatingResolver(),
        auth=EchoingAuthority(),
        reader=RecordingReader(),
    )

    assert observed == [1024]


def test_callbacks_cannot_redirect_the_authoritative_artifact() -> None:
    redirected_content = b"redirected-artifact"
    redirected_digest = sha256(redirected_content).hexdigest()
    redirected_artifact = f"document_artifact:{uuid4()}"
    calls: list[str] = []

    class MutatingAuthority:
        def authorize_document_retrieval(
            self,
            request: DocumentRetrievalQuery,
            resolved: DocumentRetrievalScope,
        ) -> DocumentRetrievalAuthorization:
            object.__setattr__(resolved, "artifact_reference", redirected_artifact)
            object.__setattr__(resolved, "artifact_digest_sha256", redirected_digest)
            return authorization(
                artifact_reference=redirected_artifact,
                artifact_digest_sha256=redirected_digest,
            )

    class RecordingReader:
        def read_document_artifact(self, artifact_reference: str, max_bytes: int) -> DocumentArtifact:
            calls.append(artifact_reference)
            return DocumentArtifact(redirected_content, redirected_digest)

    with pytest.raises(HrDocumentRetrievalError, match="exact retrieval scope"):
        execute(
            auth=MutatingAuthority(),
            reader=RecordingReader(),
        )

    assert calls == []


def test_capability_validation_occurs_before_protected_metadata_resolution() -> None:
    calls: list[str] = []
    resolver = Resolver(calls=calls)
    with pytest.raises(HrDocumentRetrievalError, match="authority must provide"):
        execute(resolver=resolver, auth=object())
    assert calls == []
    with pytest.raises(HrDocumentRetrievalError, match="artifact_reader must provide"):
        execute(resolver=resolver, reader=object())
    assert calls == []
    with pytest.raises(HrDocumentRetrievalError, match="audit_writer must provide"):
        execute(resolver=resolver, audit=object())
    assert calls == []
    with pytest.raises(HrDocumentRetrievalError, match="metadata_resolver must provide"):
        execute(resolver=object())


def test_invalid_reference_digest_time_and_result_construction_fail_closed() -> None:
    with pytest.raises(HrDocumentRetrievalError, match="canonical operational UUID"):
        query(tenant_record_id=str(UUID(int=0)))
    with pytest.raises(HrDocumentRetrievalError, match="document_record_reference"):
        query(document_record_reference="document_record:not-a-uuid")
    with pytest.raises(HrDocumentRetrievalError, match="artifact_digest_sha256"):
        scope(artifact_digest_sha256="A" * 64)
    with pytest.raises(HrDocumentRetrievalError, match="reviewed_at"):
        authorization(reviewed_at=datetime(2026, 8, 25, 13, 55))
    with pytest.raises(HrDocumentRetrievalError, match="result content"):
        DocumentRetrievalResult(b"", "application/pdf", "b" * 64)
    with pytest.raises(HrDocumentRetrievalError, match="retrieval_state"):
        DocumentRetrievalResult(
            CONTENT,
            "application/pdf",
            "b" * 64,
            retrieval_state="other_state",
        )
    with pytest.raises(HrDocumentRetrievalError, match="decision_authority_state"):
        DocumentRetrievalResult(
            CONTENT,
            "application/pdf",
            "b" * 64,
            decision_authority_state="authoritative",
        )


def test_redacted_reprs_do_not_leak_content_or_correlations() -> None:
    assert TENANT not in repr(query())
    assert PERSON not in repr(scope())
    assert REQUESTER not in repr(authorization())
    assert CONTENT.decode() not in repr(DocumentArtifact(CONTENT, CONTENT_DIGEST))
    result = DocumentRetrievalResult(CONTENT, "application/pdf", "b" * 64)
    assert CONTENT.decode() not in repr(result)


def test_validation_edge_paths_cover_noncanonical_and_hostile_primitives() -> None:
    class ForgedText(str):
        pass

    with pytest.raises(HrDocumentRetrievalError, match="canonical operational UUID"):
        query(tenant_record_id="not-a-uuid")
    with pytest.raises(HrDocumentRetrievalError, match="canonical operational UUID"):
        query(tenant_record_id=TENANT.upper())
    with pytest.raises(HrDocumentRetrievalError, match="document_record_reference"):
        query(document_record_reference=ForgedText(DOCUMENT))
    with pytest.raises(HrDocumentRetrievalError, match="document_record_reference"):
        query(document_record_reference="x" * 161)
    with pytest.raises(HrDocumentRetrievalError, match="document_record_reference"):
        query(document_record_reference=f"wrong_namespace:{uuid4()}")
    with pytest.raises(HrDocumentRetrievalError, match="document_record_reference"):
        query(document_record_reference="document_record:")
    from uuid import uuid1

    with pytest.raises(HrDocumentRetrievalError, match="document_record_reference"):
        query(document_record_reference=f"document_record:{uuid1()}")
    with pytest.raises(HrDocumentRetrievalError, match="purpose_code"):
        query(purpose_code=ForgedText("employee_file_review"))
    with pytest.raises(HrDocumentRetrievalError, match="purpose_code"):
        query(purpose_code="purpose_" + "x" * 70)
    with pytest.raises(HrDocumentRetrievalError, match="media_type"):
        scope(media_type=ForgedText("application/pdf"))
    with pytest.raises(HrDocumentRetrievalError, match="media_type"):
        scope(media_type="a/" + "b" * 130)
    with pytest.raises(HrDocumentRetrievalError, match="max_bytes"):
        query(max_bytes=16 * 1024 * 1024 + 1)


def test_timezone_provider_failures_are_normalized() -> None:
    from datetime import tzinfo

    class RaisingZone(tzinfo):
        def utcoffset(self, dt: datetime | None) -> timedelta | None:
            raise RuntimeError("hostile timezone")

        def dst(self, dt: datetime | None) -> timedelta | None:
            return None

    class OffsetlessZone(tzinfo):
        def utcoffset(self, dt: datetime | None) -> timedelta | None:
            return None

        def dst(self, dt: datetime | None) -> timedelta | None:
            return None

    raising = datetime(2026, 8, 25, 13, 55, tzinfo=RaisingZone())
    with pytest.raises(HrDocumentRetrievalError, match="timezone offset could not be resolved"):
        authorization(reviewed_at=raising)
    offsetless = datetime(2026, 8, 25, 13, 55, tzinfo=OffsetlessZone())
    with pytest.raises(HrDocumentRetrievalError, match="concrete UTC offset"):
        authorization(reviewed_at=offsetless)
    with pytest.raises(HrDocumentRetrievalError, match="reviewed_at"):
        authorization(reviewed_at="not-a-datetime")


def test_wrong_host_return_types_fail_closed() -> None:
    class BadResolver:
        def resolve_document_scope(self, request: DocumentRetrievalQuery) -> object:
            return object()

    class BadAuthority:
        def authorize_document_retrieval(
            self,
            request: DocumentRetrievalQuery,
            resolved: DocumentRetrievalScope,
        ) -> object:
            return object()

    class BadReader:
        def read_document_artifact(self, artifact_reference: str, max_bytes: int) -> object:
            return object()

    with pytest.raises(HrDocumentRetrievalError, match="DocumentRetrievalScope"):
        execute(resolver=BadResolver())
    with pytest.raises(HrDocumentRetrievalError, match="DocumentRetrievalAuthorization"):
        execute(auth=BadAuthority())
    with pytest.raises(HrDocumentRetrievalError, match="DocumentArtifact"):
        execute(reader=BadReader())
    with pytest.raises(HrDocumentRetrievalError, match="DocumentRetrievalQuery"):
        retrieve_hr_document(
            query=object(),  # type: ignore[arg-type]
            metadata_resolver=Resolver(),
            authority=Authority(),
            artifact_reader=Reader(),
            audit_writer=Audit(),
        )


def test_mutated_empty_or_digest_inconsistent_artifacts_fail_closed() -> None:
    empty = DocumentArtifact(CONTENT, CONTENT_DIGEST)
    object.__setattr__(empty, "content", b"")
    with pytest.raises(HrDocumentRetrievalError, match="non-empty built-in bytes"):
        execute(reader=Reader(empty))

    inconsistent = DocumentArtifact(CONTENT, CONTENT_DIGEST)
    object.__setattr__(inconsistent, "content", b"different")
    with pytest.raises(HrDocumentRetrievalError, match="digest does not match"):
        execute(reader=Reader(inconsistent))

    bad_digest = DocumentArtifact(CONTENT, CONTENT_DIGEST)
    object.__setattr__(bad_digest, "digest_sha256", "BAD")
    with pytest.raises(HrDocumentRetrievalError, match="digest_sha256"):
        execute(reader=Reader(bad_digest))


def test_result_exact_type_metadata_and_default_clock_path() -> None:
    class ForgedText(str):
        pass

    with pytest.raises(HrDocumentRetrievalError, match="result content"):
        DocumentRetrievalResult(  # type: ignore[arg-type]
            bytearray(CONTENT),
            "application/pdf",
            "b" * 64,
        )
    with pytest.raises(HrDocumentRetrievalError, match="retrieval_state"):
        DocumentRetrievalResult(
            CONTENT,
            "application/pdf",
            "b" * 64,
            retrieval_state=ForgedText("retrieved_after_authorization_and_audit"),
        )
    with pytest.raises(HrDocumentRetrievalError, match="decision_authority_state"):
        DocumentRetrievalResult(
            CONTENT,
            "application/pdf",
            "b" * 64,
            decision_authority_state=ForgedText("not_authorized_for_employment_decision"),
        )
    assert execute().content == CONTENT


def test_authorization_binds_retention_and_classification_scope() -> None:
    with pytest.raises(HrDocumentRetrievalError, match="retention_state"):
        authorization(retention_state="disposed_record")
    with pytest.raises(HrDocumentRetrievalError, match="classification_code"):
        authorization(classification_code="public_record")
