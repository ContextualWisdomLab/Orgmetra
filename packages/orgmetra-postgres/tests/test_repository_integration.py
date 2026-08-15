"""Real PostgreSQL integration tests for the Orgmetra persistence boundary."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.errors import ObjectNotInPrerequisiteState

from orgmetra_postgres import (
    PostgresPeopleRepository,
    PurposeContext,
    RepositoryConflictError,
)


@pytest.fixture(scope="session")
def application_dsn() -> Iterator[str]:
    """Create a fresh schema and a non-bypass application database role."""

    admin_dsn = os.environ.get("ORGMETRA_TEST_ADMIN_DATABASE_URL")
    if admin_dsn is None:
        pytest.skip("ORGMETRA_TEST_ADMIN_DATABASE_URL is required")

    repository_root = Path(__file__).resolve().parents[3]
    migration_paths = sorted(
        (repository_root / "database" / "migrations").glob("*.sql")
    )
    assert [path.name for path in migration_paths][:2] == [
        "0001_foundation_schema.sql",
        "0002_tenant_audit_boundary.sql",
    ]

    with psycopg.connect(admin_dsn, autocommit=True) as connection:
        connection.execute("DROP SCHEMA public CASCADE")
        connection.execute("CREATE SCHEMA public")
        role_exists = connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = 'orgmetra_test_app'"
        ).fetchone()
        if role_exists is not None:
            connection.execute("DROP OWNED BY orgmetra_test_app")
            connection.execute("DROP ROLE orgmetra_test_app")
        for migration_path in migration_paths:
            connection.execute(migration_path.read_text(encoding="utf-8"))

        connection.execute(
            """
            CREATE ROLE orgmetra_test_app
            LOGIN PASSWORD 'orgmetra_test_password'
            NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS
            """
        )
        connection.execute("GRANT USAGE ON SCHEMA public TO orgmetra_test_app")
        connection.execute(
            "GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO orgmetra_test_app"
        )
        connection.execute(
            "GRANT UPDATE, DELETE ON audit_event TO orgmetra_test_app"
        )
        connection.execute(
            "GRANT EXECUTE ON FUNCTION current_tenant_reference() TO orgmetra_test_app"
        )

    connection_parts = conninfo_to_dict(admin_dsn)
    connection_parts.update(
        user="orgmetra_test_app",
        password="orgmetra_test_password",
    )
    yield make_conninfo(**connection_parts)


def _context(tenant_reference: UUID, *, purpose_code: str = "hr_admin") -> PurposeContext:
    return PurposeContext(
        tenant_reference=tenant_reference,
        actor_reference=uuid4(),
        purpose_code=purpose_code,
        correlation_reference=uuid4(),
        decision_reference=uuid4(),
        evidence_reference="evidence://integration-test",
    )


def test_tenant_person_audit_and_rls_round_trip(application_dsn: str) -> None:
    repository = PostgresPeopleRepository(application_dsn)
    tenant_a = uuid4()
    tenant_b = uuid4()
    context_a = _context(tenant_a)
    context_b = _context(tenant_b)

    assert repository.create_tenant(context_a, "Acme Korea") == tenant_a
    assert repository.create_tenant(context_a, "Acme Korea") == tenant_a
    assert repository.create_tenant(context_b, "Other Company") == tenant_b
    with pytest.raises(RepositoryConflictError, match="different data"):
        repository.create_tenant(context_a, "Renamed Without Revision")

    person_id = uuid4()
    recorded_at = datetime(2026, 8, 15, 8, 30, tzinfo=timezone.utc)
    created = repository.create_person(
        context_a,
        person_record_id=person_id,
        display_name="  Seongho Bae  ",
        effective_from=date(2026, 8, 15),
        recorded_at=recorded_at,
    )
    assert created.display_name == "Seongho Bae"
    assert created.recorded_from == recorded_at
    assert repository.create_person(
        context_a,
        person_record_id=person_id,
        display_name="Seongho Bae",
        effective_from=date(2026, 8, 15),
        recorded_at=recorded_at,
    ) == created
    with pytest.raises(RepositoryConflictError, match="different data"):
        repository.create_person(
            context_a,
            person_record_id=person_id,
            display_name="Different Person",
            effective_from=date(2026, 8, 15),
        )

    assert repository.get_person(context_a, person_id) == created
    assert repository.get_person(context_b, person_id) is None
    events = repository.list_audit_events(context_a, person_id)
    assert [(event.action_code, event.purpose_code) for event in events] == [
        ("person_created", "hr_admin")
    ]
    assert repository.list_audit_events(context_b, person_id) == ()

    with psycopg.connect(application_dsn) as connection:
        assert connection.execute("SELECT count(*) FROM person_record").fetchone() == (0,)


def test_candidate_link_is_idempotent_and_append_only(application_dsn: str) -> None:
    identifiers = iter(uuid4() for _ in range(20))
    repository = PostgresPeopleRepository(
        application_dsn,
        identifier_factory=lambda: next(identifiers),
    )
    tenant_id = uuid4()
    context = _context(tenant_id, purpose_code="talent_acquisition")
    repository.create_tenant(context, "Candidate Test Tenant")

    candidate_id = uuid4()
    candidate = repository.create_candidate(
        context,
        candidate_profile_id=candidate_id,
        application_status_code="structured_screen",
    )
    assert candidate.application_status_code == "structured_screen"
    assert repository.create_candidate(
        context,
        candidate_profile_id=candidate_id,
        application_status_code="structured_screen",
    ) == candidate
    with pytest.raises(RepositoryConflictError, match="different data"):
        repository.create_candidate(
            context,
            candidate_profile_id=candidate_id,
            application_status_code="offer",
        )

    person_id = uuid4()
    repository.create_person(
        context,
        person_record_id=person_id,
        display_name="Candidate Worker",
        effective_from=date(2026, 9, 1),
    )
    explicit_link_id = uuid4()
    link = repository.link_candidate_to_worker(
        context,
        candidate_profile_id=candidate_id,
        person_record_id=person_id,
        candidate_worker_link_id=explicit_link_id,
    )
    assert link.candidate_worker_link_id == explicit_link_id
    assert repository.link_candidate_to_worker(
        context,
        candidate_profile_id=candidate_id,
        person_record_id=person_id,
    ) == link

    other_person_id = uuid4()
    repository.create_person(
        context,
        person_record_id=other_person_id,
        display_name="Other Worker",
        effective_from=date(2026, 9, 1),
    )
    with pytest.raises(RepositoryConflictError, match="different worker"):
        repository.link_candidate_to_worker(
            context,
            candidate_profile_id=candidate_id,
            person_record_id=other_person_id,
        )

    with psycopg.connect(application_dsn) as connection:
        with pytest.raises(
            ObjectNotInPrerequisiteState,
            match="immutable Orgmetra facts",
        ):
            with connection.transaction():
                connection.execute(
                    "SELECT set_config(%s, %s, true)",
                    ("orgmetra.tenant_reference", str(tenant_id)),
                )
                connection.execute(
                    """
                    UPDATE audit_event
                    SET purpose_code = 'changed'
                    WHERE resource_record_id = %s
                    """,
                    (person_id,),
                )


def test_invalid_input_and_relationship_failure_are_fail_closed(
    application_dsn: str,
) -> None:
    repository = PostgresPeopleRepository(application_dsn)
    tenant_id = uuid4()
    context = _context(tenant_id)

    with pytest.raises(ValueError, match="tenant_name"):
        repository.create_tenant(context, " ")
    with pytest.raises(ValueError, match="tenant_name"):
        repository.create_tenant(context, "x" * 201)

    repository.create_tenant(context, "Validation Tenant")
    with pytest.raises(ValueError, match="display_name"):
        repository.create_person(
            context,
            person_record_id=uuid4(),
            display_name=" ",
            effective_from=date(2026, 1, 1),
        )
    with pytest.raises(ValueError, match="display_name"):
        repository.create_person(
            context,
            person_record_id=uuid4(),
            display_name="x" * 301,
            effective_from=date(2026, 1, 1),
        )
    with pytest.raises(ValueError, match="effective_to"):
        repository.create_person(
            context,
            person_record_id=uuid4(),
            display_name="Invalid Period",
            effective_from=date(2026, 2, 1),
            effective_to=date(2026, 2, 1),
        )
    with pytest.raises(ValueError, match="application_status_code"):
        repository.create_candidate(
            context,
            candidate_profile_id=uuid4(),
            application_status_code="Needs-Review",
        )
    with pytest.raises(ValueError, match="application_status_code"):
        repository.create_candidate(
            context,
            candidate_profile_id=uuid4(),
            application_status_code="x" * 65,
        )
    with pytest.raises(RepositoryConflictError, match="constraint"):
        repository.link_candidate_to_worker(
            context,
            candidate_profile_id=uuid4(),
            person_record_id=uuid4(),
        )
