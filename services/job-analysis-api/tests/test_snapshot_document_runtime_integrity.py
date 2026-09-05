"""Regressions for executable posted snapshot values before authorization."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo

import pytest

from orgmetra_job_analysis_api.snapshot import snapshot_from_document
from fixtures import TENANT, clinical_psychologist_document


class _ExecutableMapping(dict):
    """Trip if snapshot parsing iterates or reads a caller-defined mapping subtype."""

    def __iter__(self):
        """Reject parser iteration before exact container validation."""
        raise AssertionError("mapping subtype iteration executed")

    def get(self, key: object, default: object = None) -> object:
        """Reject parser field reads before exact container validation."""
        raise AssertionError("mapping subtype get executed")


class _ExecutableList(list):
    """Trip if snapshot parsing consumes a caller-defined list subtype."""

    def __len__(self) -> int:
        """Reject truthiness/size checks before exact container validation."""
        raise AssertionError("list subtype length executed")

    def __iter__(self):
        """Reject item iteration before exact container validation."""
        raise AssertionError("list subtype iteration executed")


class _ExecutableText(str):
    """Trip if validation executes caller-defined string behavior."""

    def replace(self, old: str, new: str, count: int = -1) -> str:
        """Reject ISO timestamp normalization before exact text validation."""
        raise AssertionError("text subtype replace executed")

    def split(self, sep: str | None = None, maxsplit: int = -1) -> list[str]:
        """Reject kernel text normalization before exact leaf validation."""
        raise AssertionError("text subtype split executed")


class _ExecutableFieldName(str):
    """Trip if unknown-field validation hashes a caller-defined key before exact gating."""

    armed: bool

    def __new__(cls, value: str):
        """Create an initially inert key so the test mapping itself can be assembled."""
        instance = super().__new__(cls, value)
        instance.armed = False
        return instance

    def __hash__(self) -> int:
        """Reject set membership after the fixture is armed."""
        if self.armed:
            raise AssertionError("field-name subtype hash executed")
        return str.__hash__(self)

    def __eq__(self, other: object) -> bool:
        """Preserve normal string equality while hash remains the execution tripwire."""
        return bool(str.__eq__(self, other))


class _ExecutableInteger(int):
    """Trip if kernel ordinal validation compares a caller-defined integer subtype."""

    def __ge__(self, other: object) -> bool:
        """Reject lower-bound comparison before exact integer validation."""
        raise AssertionError("integer subtype comparison executed")

    def __le__(self, other: object) -> bool:
        """Reject upper-bound comparison before exact integer validation."""
        raise AssertionError("integer subtype comparison executed")

    def __lt__(self, other: object) -> bool:
        """Reject strict lower-bound comparison before exact integer validation."""
        raise AssertionError("integer subtype comparison executed")

    def __gt__(self, other: object) -> bool:
        """Reject strict upper-bound comparison before exact integer validation."""
        raise AssertionError("integer subtype comparison executed")


class _ExecutableDateTime(datetime):
    """Trip if timezone validation consumes a caller-defined datetime subtype."""

    def utcoffset(self):
        """Reject timezone behavior before exact datetime validation."""
        raise AssertionError("datetime subtype utcoffset executed")


class _ExecutableTimezone(tzinfo):
    """Trip if an exact datetime can delegate validation to caller-defined tzinfo."""

    def utcoffset(self, value: datetime | None) -> timedelta:
        """Reject caller-controlled UTC offset computation."""
        raise AssertionError("timezone provider utcoffset executed")

    def dst(self, value: datetime | None) -> timedelta:
        """Provide the abstract method without making it usable by the parser."""
        return timedelta(0)


def test_rejects_executable_top_level_mapping_before_iteration() -> None:
    """The posted document must be an inert built-in mapping before any field scan."""
    posted = _ExecutableMapping(clinical_psychologist_document())

    with pytest.raises(ValueError, match="snapshot document must be an object"):
        snapshot_from_document(posted, tenant_record_id=TENANT)


def test_rejects_executable_field_name_before_hash_or_membership() -> None:
    """Exact built-in field names must be established before schema membership checks."""
    posted = clinical_psychologist_document()
    value = posted.pop("analysis_record_id")
    field_name = _ExecutableFieldName("analysis_record_id")
    posted[field_name] = value
    field_name.armed = True

    with pytest.raises(ValueError, match="field names must be exact built-in text"):
        snapshot_from_document(posted, tenant_record_id=TENANT)


def test_rejects_executable_task_list_before_truthiness_or_iteration() -> None:
    """Repeated snapshot members must be inert built-in lists before size checks."""
    posted = clinical_psychologist_document()
    posted["tasks"] = _ExecutableList(posted["tasks"])

    with pytest.raises(ValueError, match="tasks must be a non-empty list"):
        snapshot_from_document(posted, tenant_record_id=TENANT)


def test_rejects_executable_nested_source_mapping_before_field_reads() -> None:
    """Nested evidence objects must be exact mappings before `.get` or iteration."""
    posted = clinical_psychologist_document()
    first_task = dict(posted["tasks"][0])
    first_task["source"] = _ExecutableMapping(first_task["source"])
    posted["tasks"] = [first_task, *posted["tasks"][1:]]

    with pytest.raises(ValueError, match="source must be an object"):
        snapshot_from_document(posted, tenant_record_id=TENANT)


def test_rejects_executable_task_text_before_kernel_normalization() -> None:
    """Leaf text must be exact built-in text before kernel `.split` normalization."""
    posted = clinical_psychologist_document()
    first_task = dict(posted["tasks"][0])
    first_task["task_statement"] = _ExecutableText(first_task["task_statement"])
    posted["tasks"] = [first_task, *posted["tasks"][1:]]

    with pytest.raises(ValueError, match="task_statement must be exact built-in text"):
        snapshot_from_document(posted, tenant_record_id=TENANT)


def test_rejects_executable_rating_before_kernel_comparison() -> None:
    """Ordinal ratings must be exact built-in integers before range comparison."""
    posted = clinical_psychologist_document()
    first_task = dict(posted["tasks"][0])
    first_task["importance_level"] = _ExecutableInteger(first_task["importance_level"])
    posted["tasks"] = [first_task, *posted["tasks"][1:]]

    with pytest.raises(ValueError, match="importance_level must be an exact built-in integer"):
        snapshot_from_document(posted, tenant_record_id=TENANT)


def test_rejects_non_boolean_essential_flag_at_request_boundary() -> None:
    """Boolean relationship flags must not reuse the integer acceptance surface."""
    posted = clinical_psychologist_document()
    first_link = dict(posted["task_ksao_links"][0])
    first_link["essential_for_task"] = 1
    posted["task_ksao_links"] = [first_link, *posted["task_ksao_links"][1:]]

    with pytest.raises(ValueError, match="essential_for_task must be an exact built-in boolean"):
        snapshot_from_document(posted, tenant_record_id=TENANT)


def test_rejects_executable_timestamp_text_before_replace() -> None:
    """ISO timestamp parsing must exact-gate text before `.replace` can execute."""
    posted = clinical_psychologist_document()
    posted["recorded_at"] = _ExecutableText(posted["recorded_at"])

    with pytest.raises(ValueError, match="recorded_at must be an ISO-8601 datetime"):
        snapshot_from_document(posted, tenant_record_id=TENANT)


def test_rejects_executable_datetime_before_timezone_behavior() -> None:
    """Direct Python datetime support must not admit executable datetime subtypes."""
    posted = clinical_psychologist_document()
    posted["recorded_at"] = _ExecutableDateTime(
        2026,
        8,
        18,
        5,
        0,
        tzinfo=timezone.utc,
    )

    with pytest.raises(ValueError, match="recorded_at must be an ISO-8601 datetime"):
        snapshot_from_document(posted, tenant_record_id=TENANT)


def test_rejects_executable_timezone_provider_before_utcoffset() -> None:
    """An exact datetime must not delegate trust validation to caller-defined tzinfo."""
    posted = clinical_psychologist_document()
    posted["recorded_at"] = datetime(
        2026,
        8,
        18,
        5,
        0,
        tzinfo=_ExecutableTimezone(),
    )

    with pytest.raises(ValueError, match="recorded_at must use a fixed UTC offset"):
        snapshot_from_document(posted, tenant_record_id=TENANT)
