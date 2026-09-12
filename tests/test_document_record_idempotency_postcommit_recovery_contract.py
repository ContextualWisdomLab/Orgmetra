"""Regression contracts for post-commit document-record recovery acceptance."""

from pathlib import Path


COMPANION = Path(__file__).with_name(
    "document_record_idempotency_postcommit_recovery_companion.sh"
)


def _companion_source() -> str:
    return COMPANION.read_text(encoding="utf-8")


def test_recovery_termination_binds_checked_backend_identity() -> None:
    """Termination must consume the same backend identity that observation accepted."""

    source = _companion_source()

    assert "backend_start_epoch" in source
    assert "extract(epoch FROM activity.backend_start)::text" in source
    assert "terminate_captured_backend" in source
    assert "application_name = '${APPLICATION_NAME}'" in source
    assert "extract(epoch FROM backend_start)::text = '${backend_start_epoch}'" in source
    assert '[[ "${termination_receipt}" == "1|true" ]]' in source


def test_recovery_session_name_is_execution_unique() -> None:
    """Concurrent or leaked acceptance sessions must not share one global marker."""

    source = _companion_source()

    assert "uuid.uuid4().hex[:24]" in source
    assert (
        'APPLICATION_NAME="orgmetra_document_idempotency_lost_${APPLICATION_SUFFIX}"'
        in source
    )
