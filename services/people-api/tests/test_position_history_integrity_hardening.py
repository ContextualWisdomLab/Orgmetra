"""Regression contracts for Position-history retained-authority boundaries."""

from __future__ import annotations

from datetime import date, datetime, timezone
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.position_history import (
    PositionHistoryIntegrityError,
    PositionHistoryReadPort,
    PositionHistoryRecord,
    _authorized_field_value,
    read_position_history,
)

TENANT = UUID("0198a413-7000-7000-8000-000000000001")
OTHER_TENANT = UUID("0198a413-7000-7000-8000-000000000002")
POSITION = UUID("0198a413-7000-7000-8000-000000000010")
OTHER_POSITION = UUID("0198a413-7000-7000-8000-000000000011")
VERSION = UUID("0198a413-7000-7000-8000-000000000020")
ORGANIZATION = UUID("0198a413-7000-7000-8000-000000000030")
JOB = UUID("0198a413-7000-7000-8000-000000000040")
KNOWN_AT = datetime(2026, 8, 30, 2, 0, tzinfo=timezone.utc)


def _record(*, position_record_id: UUID = POSITION) -> PositionHistoryRecord:
    return PositionHistoryRecord(
        tenant_record_id=TENANT,
        position_record_id=position_record_id,
        position_record_version_id=VERSION,
        organization_unit_id=ORGANIZATION,
        job_profile_id=JOB,
        position_status_code="active",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        recorded_from=datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc),
        recorded_to=None,
    )


def _principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse:hr-operator",
        granted_scope_codes=frozenset({"orgmetra.people.position_history.read"}),
    )


def _policy(fields: frozenset[str]) -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="position-history-hardening-v1",
        resource_kind="position_history",
        purpose_code="workforce_position_review",
        operation_code="read_record",
        required_scope_code="orgmetra.people.position_history.read",
        permitted_fields=fields,
    )


class EmptyPort:
    def __init__(self) -> None:
        self.calls = 0

    def read_position_history(self, **_: object) -> tuple[PositionHistoryRecord, ...]:
        self.calls += 1
        return ()


class DynamicLookupTrapPort:
    def __getattribute__(self, name: str):
        if name == "read_position_history":
            raise AssertionError("instance lookup must not select the protected capability")
        return object.__getattribute__(self, name)

    def read_position_history(self, **_: object) -> tuple[PositionHistoryRecord, ...]:
        return ()


class ProtocolDefaultPort(PositionHistoryReadPort):
    """Concrete subtype that inherits only the protocol placeholder capability."""


class MutatingPositionPort:
    def read_position_history(
        self,
        *,
        tenant_record_id: UUID,
        position_record_id: UUID,
        known_at: datetime,
    ) -> tuple[PositionHistoryRecord, ...]:
        del tenant_record_id, known_at
        object.__setattr__(position_record_id, "int", OTHER_POSITION.int)
        return (_record(position_record_id=OTHER_POSITION),)


class PositionHistoryIntegrityHardeningTests(unittest.TestCase):
    def test_record_detaches_constructor_uuid_aliases(self) -> None:
        tenant_alias = UUID(str(TENANT))
        position_alias = UUID(str(POSITION))
        version_alias = UUID(str(VERSION))
        organization_alias = UUID(str(ORGANIZATION))
        job_alias = UUID(str(JOB))
        record = PositionHistoryRecord(
            tenant_record_id=tenant_alias,
            position_record_id=position_alias,
            position_record_version_id=version_alias,
            organization_unit_id=organization_alias,
            job_profile_id=job_alias,
            position_status_code="active",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            recorded_from=datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc),
            recorded_to=None,
        )

        object.__setattr__(tenant_alias, "int", OTHER_TENANT.int)
        object.__setattr__(position_alias, "int", OTHER_POSITION.int)
        object.__setattr__(version_alias, "int", UUID(int=41).int)
        object.__setattr__(organization_alias, "int", UUID(int=42).int)
        object.__setattr__(job_alias, "int", UUID(int=43).int)

        self.assertEqual(record.tenant_record_id, TENANT)
        self.assertEqual(record.position_record_id, POSITION)
        self.assertEqual(record.position_record_version_id, VERSION)
        self.assertEqual(record.organization_unit_id, ORGANIZATION)
        self.assertEqual(record.job_profile_id, JOB)

    def test_request_position_identity_cannot_change_after_authorization(self) -> None:
        request_position = UUID(str(POSITION))
        with self.assertRaisesRegex(PositionHistoryIntegrityError, "authorized target"):
            read_position_history(
                principal=_principal(),
                tenant_record_id=TENANT,
                position_record_id=request_position,
                known_at=KNOWN_AT,
                purpose_code="workforce_position_review",
                requested_fields=frozenset({"position_status_code"}),
                policy=_policy(frozenset({"position_status_code"})),
                read_port=MutatingPositionPort(),
            )

    def test_unsupported_authorized_schema_fails_before_empty_persistence_read(self) -> None:
        port = EmptyPort()
        with self.assertRaisesRegex(PositionHistoryIntegrityError, "unsupported Position-history field"):
            read_position_history(
                principal=_principal(),
                tenant_record_id=TENANT,
                position_record_id=POSITION,
                known_at=KNOWN_AT,
                purpose_code="workforce_position_review",
                requested_fields=frozenset({"future_sensitive_field"}),
                policy=_policy(frozenset({"future_sensitive_field"})),
                read_port=port,
            )
        self.assertEqual(port.calls, 0)

    def test_unsupported_field_serializer_guard_fails_closed(self) -> None:
        with self.assertRaisesRegex(PositionHistoryIntegrityError, "unsupported Position-history field"):
            _authorized_field_value(_record(), "future_sensitive_field")

    def test_nonconcrete_repository_capabilities_fail_before_authorization(self) -> None:
        for read_port in (object(), ProtocolDefaultPort()):
            with self.subTest(read_port_type=type(read_port).__name__):
                with self.assertRaisesRegex(TypeError, "statically callable read_position_history"):
                    read_position_history(
                        principal=_principal(),
                        tenant_record_id=TENANT,
                        position_record_id=POSITION,
                        known_at=KNOWN_AT,
                        purpose_code="workforce_position_review",
                        requested_fields=frozenset({"position_status_code"}),
                        policy=_policy(frozenset({"position_status_code"})),
                        read_port=read_port,
                    )

    def test_repository_capability_is_captured_without_instance_lookup(self) -> None:
        view = read_position_history(
            principal=_principal(),
            tenant_record_id=TENANT,
            position_record_id=POSITION,
            known_at=KNOWN_AT,
            purpose_code="workforce_position_review",
            requested_fields=frozenset({"position_status_code"}),
            policy=_policy(frozenset({"position_status_code"})),
            read_port=DynamicLookupTrapPort(),
        )
        self.assertEqual(view.entries, ())


if __name__ == "__main__":
    unittest.main()
