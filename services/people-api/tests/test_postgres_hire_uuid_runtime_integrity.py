"""Runtime-integrity contracts for durable hire UUID evidence."""

from uuid import UUID

from orgmetra_people_api.postgres_hire import _is_operational_uuid


_MAX_UUID_INT = (1 << 128) - 1


class _ExecutableUUID(UUID):
    """Expose any UUID attribute inspection performed before an exact-type gate."""

    def __getattribute__(self, name: str) -> object:
        """Fail when untrusted UUID evidence is inspected as if it were inert."""
        if name == "int":
            raise AssertionError("UUID subtype behavior executed before exact-type validation")
        return super().__getattribute__(name)


def test_hire_durable_uuid_rejects_subtype_before_identity_inspection() -> None:
    """Database-returned UUID subtypes must fail without executing subtype behavior."""
    value = _ExecutableUUID("0198a412-7100-7000-8000-000000000060")

    assert _is_operational_uuid(value) is False


def test_hire_durable_uuid_accepts_only_operational_exact_uuid_values() -> None:
    """Exact Psycopg-compatible UUID values remain valid except reserved sentinels."""
    assert _is_operational_uuid(UUID("0198a412-7100-7000-8000-000000000060")) is True
    assert _is_operational_uuid(UUID(int=0)) is False
    assert _is_operational_uuid(UUID(int=_MAX_UUID_INT)) is False
