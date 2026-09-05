"""Regression coverage for fixed PostgreSQL read projections and target identity."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, tzinfo
import unittest
from uuid import UUID
from zoneinfo import ZoneInfo

from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import JobAnalysisIntegrityError
from fixtures import ANALYSIS, JOB, OTHER_TENANT, RECORDED_AT, TENANT
from test_postgres import (
    FakeConnection,
    FakeCursor,
    _header_row,
    _ksao_rows,
    _link_rows,
    _task_rows,
)


class _EqualityForgedUUID(UUID):
    """Model DB-returned UUID evidence that forges equality before validation."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False


class _ExecutableUUID(UUID):
    """Model a durable UUID scalar that executes when kernel ownership is compared."""

    calls = 0

    def __eq__(self, other: object) -> bool:
        type(self).calls += 1
        raise AssertionError("durable UUID equality executed before exact validation")

    def __ne__(self, other: object) -> bool:
        type(self).calls += 1
        raise AssertionError("durable UUID inequality executed before exact validation")

    def __hash__(self) -> int:
        type(self).calls += 1
        raise AssertionError("durable UUID hashing executed before exact validation")


class _ExecutableDigest(str):
    """Model durable digest text whose comparison would execute adapter-owned code."""

    calls = 0

    def __eq__(self, other: object) -> bool:
        type(self).calls += 1
        raise AssertionError("durable digest equality executed before exact validation")

    def __ne__(self, other: object) -> bool:
        type(self).calls += 1
        raise AssertionError("durable digest inequality executed before exact validation")


class _ExecutableText(str):
    """Model durable text whose normalization would dispatch a custom method."""

    calls = 0

    def split(self, *args: object, **kwargs: object) -> list[str]:
        type(self).calls += 1
        raise AssertionError("durable text split executed before exact validation")


class _ExecutableInt(int):
    """Model a durable ordinal whose range comparison would execute custom code."""

    calls = 0

    def __ge__(self, other: object) -> bool:
        type(self).calls += 1
        raise AssertionError("durable integer comparison executed before exact validation")

    def __le__(self, other: object) -> bool:
        type(self).calls += 1
        raise AssertionError("durable integer comparison executed before exact validation")

    def __lt__(self, other: object) -> bool:
        type(self).calls += 1
        raise AssertionError("durable integer comparison executed before exact validation")

    def __gt__(self, other: object) -> bool:
        type(self).calls += 1
        raise AssertionError("durable integer comparison executed before exact validation")


class _ExecutableDatetime(datetime):
    """Model a durable instant whose offset lookup would execute custom code."""

    calls = 0

    def utcoffset(self) -> object:
        type(self).calls += 1
        raise AssertionError("durable datetime offset executed before exact validation")


class _ExecutableTzinfo(tzinfo):
    """Model an exact datetime carrying executable non-standard timezone evidence."""

    calls = 0

    def utcoffset(self, dt: datetime | None) -> object:
        type(self).calls += 1
        raise AssertionError("durable timezone offset executed before exact validation")

    def dst(self, dt: datetime | None) -> None:
        return None

    def tzname(self, dt: datetime | None) -> str:
        return "executable"


class _BrokenSequence(Sequence[object]):
    """Model a DB-API row sequence that fails while values are detached."""

    def __len__(self) -> int:
        return 1

    def __getitem__(self, index: int) -> object:
        raise TypeError("broken row sequence")


class PostgresReadProjectionIntegrityTests(unittest.TestCase):
    """Require every fixed read projection to match its SQL row contract."""

    def _read(self, script: list[object]) -> None:
        cursor = FakeCursor(script)
        port = PostgresJobAnalysisPort(lambda: FakeConnection(cursor))
        port.read_snapshot(tenant_record_id=TENANT, analysis_record_id=ANALYSIS)

    def _valid_script(
        self,
        *,
        headers: object | None = None,
        tasks: object | None = None,
        ksaos: object | None = None,
        links: object | None = None,
    ) -> list[object]:
        return [
            None,
            None,
            [_header_row()] if headers is None else headers,
            _task_rows() if tasks is None else tasks,
            _ksao_rows() if ksaos is None else ksaos,
            _link_rows() if links is None else links,
        ]

    def test_read_rejects_invalid_snapshot_header_shape(self) -> None:
        header = _header_row()
        malformed_rows = (
            object(),
            _BrokenSequence(),
            header[:-1],
            header + ("surplus",),
            (value for value in header),
        )
        for row in malformed_rows:
            with self.subTest(row_type=type(row).__name__):
                with self.assertRaisesRegex(
                    JobAnalysisIntegrityError,
                    "job_analysis_snapshot row has invalid shape",
                ):
                    self._read(self._valid_script(headers=[row]))

    def test_read_rejects_invalid_task_projection_shape(self) -> None:
        canonical = _task_rows()
        malformed_rows = (
            object(),
            canonical[0][:-1],
            canonical[0] + ("surplus",),
            (value for value in canonical[0]),
        )
        for row in malformed_rows:
            with self.subTest(row_type=type(row).__name__):
                rows = list(canonical)
                rows[0] = row  # type: ignore[assignment]
                with self.assertRaisesRegex(
                    JobAnalysisIntegrityError,
                    "job_analysis_task_item row has invalid shape",
                ):
                    self._read(self._valid_script(tasks=rows))

    def test_read_rejects_invalid_ksao_projection_shape(self) -> None:
        canonical = _ksao_rows()
        malformed_rows = (
            object(),
            canonical[0][:-1],
            canonical[0] + ("surplus",),
            (value for value in canonical[0]),
        )
        for row in malformed_rows:
            with self.subTest(row_type=type(row).__name__):
                rows = list(canonical)
                rows[0] = row  # type: ignore[assignment]
                with self.assertRaisesRegex(
                    JobAnalysisIntegrityError,
                    "job_analysis_ksao_item row has invalid shape",
                ):
                    self._read(self._valid_script(ksaos=rows))

    def test_read_rejects_invalid_link_projection_shape(self) -> None:
        canonical = _link_rows()
        malformed_rows = (
            object(),
            canonical[0][:-1],
            canonical[0] + ("surplus",),
            (value for value in canonical[0]),
        )
        for row in malformed_rows:
            with self.subTest(row_type=type(row).__name__):
                rows = list(canonical)
                rows[0] = row  # type: ignore[assignment]
                with self.assertRaisesRegex(
                    JobAnalysisIntegrityError,
                    "job_analysis_task_ksao_link row has invalid shape",
                ):
                    self._read(self._valid_script(links=rows))

    def test_read_exact_validates_returned_target_identity_before_equality(self) -> None:
        forged_tenant = _EqualityForgedUUID(str(OTHER_TENANT))
        forged_analysis = _EqualityForgedUUID("0198a412-6000-7000-8000-000000000499")
        cases = (
            (
                _header_row(tenant_record_id=forged_tenant),
                "job_analysis_snapshot.tenant_record_id row has invalid identity",
            ),
            (
                _header_row(analysis_record_id=forged_analysis),
                "job_analysis_snapshot.analysis_record_id row has invalid identity",
            ),
        )
        for header, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(JobAnalysisIntegrityError, expected):
                    self._read(self._valid_script(headers=[header]))

    def test_read_rejects_executable_stored_job_identity_before_kernel_use(self) -> None:
        canonical = _header_row()
        executable_job = _ExecutableUUID(str(JOB))
        header = canonical[:2] + (executable_job,) + canonical[3:]
        _ExecutableUUID.calls = 0

        with self.assertRaisesRegex(
            JobAnalysisIntegrityError,
            "job_analysis_snapshot.job_profile_id row has invalid identity",
        ):
            self._read(self._valid_script(headers=[header]))

        self.assertEqual(_ExecutableUUID.calls, 0)

    def test_read_rejects_executable_stored_digest_before_comparison(self) -> None:
        canonical = _header_row()
        digest = _ExecutableDigest(canonical[9])
        header = canonical[:9] + (digest,) + canonical[10:]
        _ExecutableDigest.calls = 0

        with self.assertRaisesRegex(
            JobAnalysisIntegrityError,
            "job_analysis_snapshot.content_digest_sha256 row has invalid scalar evidence",
        ):
            self._read(self._valid_script(headers=[header]))

        self.assertEqual(_ExecutableDigest.calls, 0)

    def test_read_rejects_executable_task_text_before_kernel_normalization(self) -> None:
        rows = list(_task_rows())
        row = rows[0]
        rows[0] = row[:1] + (_ExecutableText(row[1]),) + row[2:]
        _ExecutableText.calls = 0

        with self.assertRaisesRegex(
            JobAnalysisIntegrityError,
            "job_analysis_task_item.task_statement row has invalid scalar evidence",
        ):
            self._read(self._valid_script(tasks=rows))

        self.assertEqual(_ExecutableText.calls, 0)

    def test_read_rejects_executable_task_level_before_kernel_comparison(self) -> None:
        rows = list(_task_rows())
        row = rows[0]
        rows[0] = row[:2] + (_ExecutableInt(row[2]),) + row[3:]
        _ExecutableInt.calls = 0

        with self.assertRaisesRegex(
            JobAnalysisIntegrityError,
            "job_analysis_task_item.importance_level row has invalid scalar evidence",
        ):
            self._read(self._valid_script(tasks=rows))

        self.assertEqual(_ExecutableInt.calls, 0)

    def test_read_rejects_executable_recorded_at_before_offset_lookup(self) -> None:
        executable = _ExecutableDatetime(
            RECORDED_AT.year,
            RECORDED_AT.month,
            RECORDED_AT.day,
            RECORDED_AT.hour,
            RECORDED_AT.minute,
            RECORDED_AT.second,
            RECORDED_AT.microsecond,
            tzinfo=RECORDED_AT.tzinfo,
        )
        canonical = _header_row()
        header = canonical[:6] + (executable,) + canonical[7:]
        _ExecutableDatetime.calls = 0

        with self.assertRaisesRegex(
            JobAnalysisIntegrityError,
            "job_analysis_snapshot.recorded_at row has invalid scalar evidence",
        ):
            self._read(self._valid_script(headers=[header]))

        self.assertEqual(_ExecutableDatetime.calls, 0)

    def test_read_rejects_exact_datetime_with_executable_timezone_before_offset_lookup(self) -> None:
        executable_timezone = _ExecutableTzinfo()
        executable = datetime(
            RECORDED_AT.year,
            RECORDED_AT.month,
            RECORDED_AT.day,
            RECORDED_AT.hour,
            RECORDED_AT.minute,
            RECORDED_AT.second,
            RECORDED_AT.microsecond,
            tzinfo=executable_timezone,
        )
        canonical = _header_row()
        header = canonical[:6] + (executable,) + canonical[7:]
        _ExecutableTzinfo.calls = 0

        with self.assertRaisesRegex(
            JobAnalysisIntegrityError,
            "job_analysis_snapshot.recorded_at row has invalid scalar evidence",
        ):
            self._read(self._valid_script(headers=[header]))

        self.assertEqual(_ExecutableTzinfo.calls, 0)

    def test_read_accepts_psycopg3_zoneinfo_timestamptz_projection(self) -> None:
        canonical = _header_row()
        zoneinfo_recorded_at = RECORDED_AT.astimezone(ZoneInfo("UTC"))
        header = canonical[:6] + (zoneinfo_recorded_at,) + canonical[7:]

        self._read(self._valid_script(headers=[header]))


if __name__ == "__main__":
    unittest.main()
