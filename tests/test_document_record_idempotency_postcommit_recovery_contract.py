"""Regression contracts for post-commit document-record recovery acceptance."""

from pathlib import Path


COMPANION = Path(__file__).with_name(
    "document_record_idempotency_postcommit_recovery_companion.sh"
)


def _companion_source() -> str:
    return COMPANION.read_text(encoding="utf-8")


def _shell_function(source: str, name: str, following_marker: str) -> str:
    start = source.index(f"{name}() {{")
    end = source.index(following_marker, start)
    return source[start:end]


def test_recovery_termination_binds_checked_backend_identity() -> None:
    """Termination must consume the same backend identity that observation accepted."""

    source = _companion_source()
    termination = _shell_function(
        source,
        "terminate_captured_backend",
        "\n}\n\ncleanup()",
    )

    # Fail closed on any second lexical occurrence, including an alternate call
    # hidden behind PostgreSQL whitespace/comments or a separate helper.
    assert source.count("pg_terminate_backend") == 1
    assert termination.count("pg_terminate_backend") == 1
    assert "pg_catalog.pg_terminate_backend(pid)" in termination
    assert "WHERE pid = ${backend_pid}" in termination
    assert "application_name = '${APPLICATION_NAME}'" in termination
    assert (
        "extract(epoch FROM backend_start)::text = '${backend_start_epoch}'"
        in termination
    )
    assert '[[ "${termination_receipt}" == "1|true" ]]' in termination

    assert "extract(epoch FROM activity.backend_start)::text" in source


def test_exit_cleanup_uses_the_same_guarded_backend_identity() -> None:
    """Abort cleanup must not introduce another backend-termination path."""

    source = _companion_source()
    cleanup = _shell_function(source, "cleanup", "\n}\ntrap cleanup EXIT")

    assert "terminate_captured_backend" in cleanup
    assert "pg_terminate_backend" not in cleanup
    assert "backend_start_epoch" in cleanup
    assert "|| true" in cleanup


def test_recovery_session_name_is_execution_unique() -> None:
    """Concurrent or leaked acceptance sessions must not share one global marker."""

    source = _companion_source()

    assert "uuid.uuid4().hex[:24]" in source
    assert (
        'APPLICATION_NAME="orgmetra_document_idempotency_lost_${APPLICATION_SUFFIX}"'
        in source
    )
