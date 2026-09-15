"""Runtime-integrity contract for durable Position parent identities."""

from uuid import UUID

from orgmetra_people_api.mutations import PeopleMutationIntegrityError
from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort
from test_people_mutations import JOB, ORGANIZATION, position_command
from test_postgres_people_mutations import (
    FakeConnection,
    RECORDED_AT,
    ScriptedCursor,
    position_authorization,
)


class _ExecutableComparableUUID(UUID):
    """Expose parent-identity comparison performed before an exact-type gate."""

    def __eq__(self, other: object) -> bool:
        """Fail if durable parent validation executes subtype equality."""
        del other
        raise AssertionError("UUID subtype equality executed before exact-type validation")

    def __ne__(self, other: object) -> bool:
        """Fail if durable parent validation executes subtype inequality."""
        del other
        raise AssertionError("UUID subtype inequality executed before exact-type validation")


def test_position_parent_uuid_subtypes_reject_before_identity_comparison() -> None:
    """Organization and Job UUID subtypes fail before their comparison hooks execute."""
    for parent_index, expected_parent in enumerate((ORGANIZATION, JOB)):
        parent_uuid = _ExecutableComparableUUID(str(expected_parent))
        parent_row: list[object] = [ORGANIZATION, JOB, RECORDED_AT]
        parent_row[parent_index] = parent_uuid
        cursor = ScriptedCursor([[], [tuple(parent_row)]], [])
        connection = FakeConnection(cursor)
        port = PostgresPeopleMutationPort(lambda: connection)

        try:
            port.create_position(
                command=position_command(),
                authorization=position_authorization(),
            )
        except PeopleMutationIntegrityError as error:
            assert str(error) == "position parent identity is invalid"
        else:
            raise AssertionError("position parent UUID subtype was not rejected")
