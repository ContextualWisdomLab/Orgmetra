"""Regression contract for inert Job Analysis read-result graphs."""

from __future__ import annotations

from datetime import datetime, timedelta, tzinfo
import unittest
from uuid import UUID

from orgmetra_hris_kernel import JobAnalysisSnapshot
from orgmetra_job_analysis_api.snapshot import (
    JobAnalysisIntegrityError,
    read_job_analysis_snapshot,
)

from fixtures import (
    ANALYSIS,
    JOB,
    TENANT,
    clinical_psychologist_snapshot,
    read_policy,
    read_principal,
)


class _ExecutableUUID(UUID):
    """Raise if response export stringifies caller-controlled identity evidence."""

    def __str__(self) -> str:
        """Fail if a low-level rewritten UUID reaches snapshot export."""
        raise AssertionError("returned snapshot UUID stringification executed")


class _ExecutableTuple(tuple[object, ...]):
    """Raise if response export iterates a caller-controlled collection."""

    def __iter__(self):  # type: ignore[override]
        """Fail if a low-level rewritten collection reaches sorting/export."""
        raise AssertionError("returned snapshot collection iteration executed")


class _ExecutableText(str):
    """Represent non-inert text that must not cross the read-result boundary."""


class _ExecutableTimezone(tzinfo):
    """Raise if datetime canonicalization delegates to caller-controlled timezone code."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Fail if response export asks the hostile timezone for an offset."""
        raise AssertionError("returned snapshot timezone offset executed")

    def dst(self, dt: datetime | None) -> timedelta:
        """Return a nominal DST value; export must not call this implementation."""
        return timedelta(0)

    def tzname(self, dt: datetime | None) -> str:
        """Return a nominal name; export must reject the timezone before use."""
        return "EXECUTABLE"


class _ReadPort:
    """Return one configured exact snapshot without normalizing live fields."""

    def __init__(self, snapshot: JobAnalysisSnapshot) -> None:
        self.snapshot = snapshot

    def read_snapshot(
        self,
        *,
        tenant_record_id: UUID,
        analysis_record_id: UUID,
    ) -> JobAnalysisSnapshot:
        """Return the configured snapshot exactly as supplied by the test."""
        return self.snapshot


def _read(snapshot: JobAnalysisSnapshot) -> None:
    """Execute the governed read path for one adversarial returned snapshot."""
    read_job_analysis_snapshot(
        principal=read_principal(),
        tenant_record_id=TENANT,
        analysis_record_id=ANALYSIS,
        purpose_code="job_analysis_read",
        policy=read_policy(),
        read_port=_ReadPort(snapshot),
    )


class ReadSnapshotGraphRuntimeIntegrityTests(unittest.TestCase):
    """Reject executable non-target graph evidence before customer export."""

    def test_root_job_identity_is_exact_gated_before_stringification(self) -> None:
        """Reject an executable Job UUID even when route target identities are valid."""
        snapshot = clinical_psychologist_snapshot()
        object.__setattr__(snapshot, "job_record_id", _ExecutableUUID(str(JOB)))

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "resolved snapshot graph"):
            _read(snapshot)

    def test_task_collection_is_exact_gated_before_iteration(self) -> None:
        """Reject an executable tuple before sorting the returned Task evidence."""
        snapshot = clinical_psychologist_snapshot()
        object.__setattr__(snapshot, "tasks", _ExecutableTuple(snapshot.tasks))

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "resolved snapshot graph"):
            _read(snapshot)

    def test_nested_task_identity_is_exact_gated_before_sort_key_stringification(self) -> None:
        """Reject executable nested UUID evidence before deterministic ordering."""
        snapshot = clinical_psychologist_snapshot()
        object.__setattr__(
            snapshot.tasks[0],
            "task_record_id",
            _ExecutableUUID(str(snapshot.tasks[0].task_record_id)),
        )

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "resolved snapshot graph"):
            _read(snapshot)

    def test_root_text_is_exact_gated_before_response_export(self) -> None:
        """Reject a text subtype even if exporting it would not call an override yet."""
        snapshot = clinical_psychologist_snapshot()
        object.__setattr__(
            snapshot,
            "analysis_version_code",
            _ExecutableText(snapshot.analysis_version_code),
        )

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "resolved snapshot graph"):
            _read(snapshot)

    def test_datetime_timezone_is_exact_gated_before_canonicalization(self) -> None:
        """Reject caller-controlled timezone behavior before `_utc_text` can execute it."""
        snapshot = clinical_psychologist_snapshot()
        object.__setattr__(
            snapshot,
            "recorded_at",
            datetime(2026, 8, 18, 5, 0, tzinfo=_ExecutableTimezone()),
        )

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "resolved snapshot graph"):
            _read(snapshot)

    def test_nested_source_timezone_is_exact_gated_before_canonicalization(self) -> None:
        """Reject executable provenance time below a Task before source export."""
        snapshot = clinical_psychologist_snapshot()
        object.__setattr__(
            snapshot.tasks[0].source,
            "retrieved_at",
            datetime(2026, 8, 18, 3, 0, tzinfo=_ExecutableTimezone()),
        )

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "resolved snapshot graph"):
            _read(snapshot)


if __name__ == "__main__":
    unittest.main()
