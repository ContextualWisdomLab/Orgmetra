"""Executable contracts for governed hire-to-employment People reads."""

from __future__ import annotations

from datetime import date
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_people_api import (
    AuthenticatedPrincipal,
    PeopleRecordIntegrityError,
    PeopleRecordNotFound,
    WorkerPeopleRecord,
    read_worker_people_record,
)

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
OTHER_TENANT = UUID("0198a412-6000-7000-8000-000000000002")
PERSON = UUID("0198a412-6000-7000-8000-000000000010")
OTHER_PERSON = UUID("0198a412-6000-7000-8000-000000000011")
EMPLOYMENT = UUID("0198a412-6000-7000-8000-000000000020")
CONVERSION = UUID("0198a412-6000-7000-8000-000000000030")
CANDIDATE = UUID("0198a412-6000-7000-8000-000000000040")
EFFECTIVE_ON = date(2026, 8, 17)


class FakePeopleReadPort:
    """Record repository calls without introducing a database dependency."""

    def __init__(self, result: WorkerPeopleRecord | None) -> None:
        self.result = result
        self.calls: list[tuple[UUID, UUID, date]] = []

    def read_worker(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        effective_on: date,
    ) -> WorkerPeopleRecord | None:
        """Return the configured record after capturing exact tenant/target/date scope."""
        self.calls.append((tenant_record_id, person_record_id, effective_on))
        return self.result


def worker_record(*, tenant_record_id: UUID = TENANT, person_record_id: UUID = PERSON) -> WorkerPeopleRecord:
    """Build one governed worker record for service-contract tests."""
    return WorkerPeopleRecord(
        tenant_record_id=tenant_record_id,
        candidate_worker_conversion_record_id=CONVERSION,
        candidate_profile_id=CANDIDATE,
        person_record_id=person_record_id,
        employment_record_id=EMPLOYMENT,
        display_name="Ada Lovelace",
        employment_status_code="active",
    )


class WorkerPeopleReadTests(unittest.TestCase):
    """Prove authorization precedes PII retrieval and lineage stays exact."""

    def setUp(self) -> None:
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({"orgmetra.people.read"}),
        )
        self.policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="v1",
            resource_kind="person_record",
            purpose_code="people_read",
            operation_code="read_record",
            required_scope_code="orgmetra.people.read",
            permitted_fields=frozenset(
                {
                    "candidate_worker_conversion_record_id",
                    "display_name",
                    "employment_status_code",
                }
            ),
        )

    def test_returns_only_authorized_worker_fields_with_exact_lineage(self) -> None:
        port = FakePeopleReadPort(worker_record())

        view = read_worker_people_record(
            principal=self.principal,
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            effective_on=EFFECTIVE_ON,
            purpose_code="people_read",
            requested_fields=frozenset(
                {
                    "candidate_worker_conversion_record_id",
                    "display_name",
                    "employment_status_code",
                }
            ),
            policy=self.policy,
            read_port=port,
        )

        self.assertEqual(view.resource_reference, f"person_record:{PERSON.hex}")
        self.assertEqual(
            view.field_values,
            (
                ("candidate_worker_conversion_record_id", str(CONVERSION)),
                ("display_name", "Ada Lovelace"),
                ("employment_status_code", "active"),
            ),
        )
        self.assertEqual(port.calls, [(TENANT, PERSON, EFFECTIVE_ON)])

    def test_denied_field_never_reaches_people_repository(self) -> None:
        port = FakePeopleReadPort(worker_record())

        with self.assertRaises(AuthorizationDeniedError):
            read_worker_people_record(
                principal=self.principal,
                tenant_record_id=TENANT,
                person_record_id=PERSON,
                effective_on=EFFECTIVE_ON,
                purpose_code="people_read",
                requested_fields=frozenset({"employment_record_id"}),
                policy=self.policy,
                read_port=port,
            )

        self.assertEqual(port.calls, [])

    def test_missing_worker_is_reported_without_exposing_persistence_details(self) -> None:
        port = FakePeopleReadPort(None)

        with self.assertRaisesRegex(PeopleRecordNotFound, "worker record is unavailable"):
            read_worker_people_record(
                principal=self.principal,
                tenant_record_id=TENANT,
                person_record_id=PERSON,
                effective_on=EFFECTIVE_ON,
                purpose_code="people_read",
                requested_fields=frozenset({"display_name"}),
                policy=self.policy,
                read_port=port,
            )

    def test_repository_target_mismatch_fails_closed(self) -> None:
        for record in (
            worker_record(tenant_record_id=OTHER_TENANT),
            worker_record(person_record_id=OTHER_PERSON),
        ):
            with self.subTest(record=record):
                port = FakePeopleReadPort(record)
                with self.assertRaisesRegex(PeopleRecordIntegrityError, "resolved worker does not match authorized target"):
                    read_worker_people_record(
                        principal=self.principal,
                        tenant_record_id=TENANT,
                        person_record_id=PERSON,
                        effective_on=EFFECTIVE_ON,
                        purpose_code="people_read",
                        requested_fields=frozenset({"display_name"}),
                        policy=self.policy,
                        read_port=port,
                    )

    def test_worker_record_rejects_reserved_identity_and_blank_business_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "operational UUID"):
            WorkerPeopleRecord(
                tenant_record_id=UUID(int=0),
                candidate_worker_conversion_record_id=CONVERSION,
                candidate_profile_id=CANDIDATE,
                person_record_id=PERSON,
                employment_record_id=EMPLOYMENT,
                display_name="Ada Lovelace",
                employment_status_code="active",
            )
        with self.assertRaisesRegex(ValueError, "display_name"):
            WorkerPeopleRecord(
                tenant_record_id=TENANT,
                candidate_worker_conversion_record_id=CONVERSION,
                candidate_profile_id=CANDIDATE,
                person_record_id=PERSON,
                employment_record_id=EMPLOYMENT,
                display_name="   ",
                employment_status_code="active",
            )
        with self.assertRaisesRegex(ValueError, "employment_status_code"):
            WorkerPeopleRecord(
                tenant_record_id=TENANT,
                candidate_worker_conversion_record_id=CONVERSION,
                candidate_profile_id=CANDIDATE,
                person_record_id=PERSON,
                employment_record_id=EMPLOYMENT,
                display_name="Ada Lovelace",
                employment_status_code="Active Employment",
            )


if __name__ == "__main__":
    unittest.main()
