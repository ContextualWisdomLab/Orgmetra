"""Executable-container regressions for generic People PostgreSQL projections."""

from __future__ import annotations

import pytest

import orgmetra_people_api.postgres_mutations as postgres_mutations
from orgmetra_people_api.mutations import PeopleMutationIntegrityError


class _ExecutableRows(list[object]):
    """Tripwire outer row collection that must be rejected before container hooks."""

    calls = 0

    def __bool__(self) -> bool:
        """Fail if durable validation asks this untrusted collection for truthiness."""
        type(self).calls += 1
        raise TypeError("outer durable row collection executed __bool__")

    def __len__(self) -> int:
        """Fail if durable validation asks this untrusted collection for cardinality."""
        type(self).calls += 1
        raise AssertionError("outer durable row collection executed __len__")

    def __getitem__(self, index: object) -> object:
        """Fail if durable validation indexes this untrusted collection."""
        type(self).calls += 1
        raise IndexError("outer durable row collection executed __getitem__")

    def __iter__(self):
        """Fail if durable validation iterates this untrusted collection."""
        type(self).calls += 1
        raise AssertionError("outer durable row collection executed __iter__")


class _ExecutableRow(tuple[object, ...]):
    """Tripwire fixed row that must be rejected before row hooks."""

    calls = 0

    def __len__(self) -> int:
        """Fail if durable validation asks this untrusted row for width."""
        type(self).calls += 1
        raise AssertionError("durable row executed __len__")

    def __iter__(self):
        """Fail if durable validation iterates this untrusted row."""
        type(self).calls += 1
        raise AssertionError("durable row executed __iter__")


@pytest.fixture(autouse=True)
def _reset_tripwires() -> None:
    """Reset shared counters so each rejection proves zero callback execution."""
    _ExecutableRows.calls = 0
    _ExecutableRow.calls = 0


def _unpack(value: object, *, row_width: int) -> tuple[tuple[object, ...], ...]:
    """Resolve the production boundary explicitly so predecessor absence is RED."""
    unpack = getattr(postgres_mutations, "_unpack_fixed_rows", None)
    assert unpack is not None, "generic People PostgreSQL adapter lacks a fixed-row trust boundary"
    return unpack(value, row_width=row_width, error_message="durable projection is invalid")


def test_fixed_rows_reject_executable_outer_collection_before_hooks() -> None:
    """Reject a list subtype before truthiness, length, indexing, or iteration executes."""
    rows = _ExecutableRows([(UUID_SENTINEL, "digest")])

    with pytest.raises(PeopleMutationIntegrityError, match="durable projection is invalid"):
        _unpack(rows, row_width=2)

    assert _ExecutableRows.calls == 0


def test_fixed_rows_reject_executable_row_before_hooks() -> None:
    """Reject a tuple subtype before width or iteration executes."""
    row = _ExecutableRow((UUID_SENTINEL, "digest"))

    with pytest.raises(PeopleMutationIntegrityError, match="durable projection is invalid"):
        _unpack([row], row_width=2)

    assert _ExecutableRow.calls == 0


def test_fixed_rows_reject_wrong_width_exact_row() -> None:
    """Reject an inert built-in row whose SQL projection width is impossible."""
    with pytest.raises(PeopleMutationIntegrityError, match="durable projection is invalid"):
        _unpack([(1, 2, 3)], row_width=2)


def test_fixed_rows_detach_exact_builtin_batches_and_rows() -> None:
    """Accept exact built-in containers and return one inert tuple-of-tuples copy."""
    source = [[1, "a"], (2, "b")]

    detached = _unpack(source, row_width=2)

    assert detached == ((1, "a"), (2, "b"))
    assert type(detached) is tuple
    assert all(type(row) is tuple for row in detached)


UUID_SENTINEL = object()
