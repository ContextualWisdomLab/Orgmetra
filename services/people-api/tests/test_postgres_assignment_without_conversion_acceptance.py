"""Real PostgreSQL acceptance for staffing an Employment without recruiting provenance."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import runpy
from uuid import UUID

from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort


def _load_acceptance_namespace() -> dict[str, object]:
    """Reuse the reviewed isolated-PostgreSQL/libpq harness without duplicating transport code."""
    source = Path(__file__).with_name("test_postgres_assignment_concurrency_acceptance.py")
    return runpy.run_path(str(source))


def test_generic_assignment_does_not_require_candidate_worker_conversion() -> None:
    """Canonical Employment/Position truth must be sufficient for a governed Assignment."""
    acceptance = _load_acceptance_namespace()
    isolated_postgres = acceptance["_isolated_postgres"]
    psql = acceptance["_psql"]
    tenant = acceptance["_TENANT"]
    person = acceptance["_PERSON_ONE"]
    employment = acceptance["_EMPLOYMENT_ONE"]
    position = acceptance["_POSITION_ONE"]
    organization = UUID("10000000-0000-7000-8004-000000000001")
    job = UUID("10000000-0000-7000-8004-000000000002")

    with isolated_postgres() as database_url:
        psql(
            database_url,
            f"""
            INSERT INTO tenant_record (tenant_record_id, tenant_reference)
            VALUES ('{tenant}', 'assignment_without_conversion');
            INSERT INTO person_record (tenant_record_id, person_record_id, recorded_from)
            VALUES ('{tenant}', '{person}', pg_catalog.clock_timestamp() - INTERVAL '5 minutes');
            INSERT INTO employment_record
                (tenant_record_id, employment_record_id, person_record_id, recorded_from)
            VALUES ('{tenant}', '{employment}', '{person}', pg_catalog.clock_timestamp() - INTERVAL '5 minutes');
            INSERT INTO employment_record_version
                (tenant_record_id, employment_record_version_id, employment_record_id,
                 employment_status_code, employment_concurrency_code, effective_from, recorded_from)
            VALUES ('{tenant}', '10000000-0000-7000-8004-000000000003', '{employment}',
                    'active', 'exclusive', DATE '2026-09-01', pg_catalog.clock_timestamp() - INTERVAL '5 minutes');
            INSERT INTO organization_unit (tenant_record_id, organization_unit_id, recorded_from)
            VALUES ('{tenant}', '{organization}', pg_catalog.clock_timestamp() - INTERVAL '5 minutes');
            INSERT INTO job_profile (tenant_record_id, job_profile_id, recorded_from)
            VALUES ('{tenant}', '{job}', pg_catalog.clock_timestamp() - INTERVAL '5 minutes');
            INSERT INTO position_record
                (tenant_record_id, position_record_id, organization_unit_id, job_profile_id, recorded_from)
            VALUES ('{tenant}', '{position}', '{organization}', '{job}', pg_catalog.clock_timestamp() - INTERVAL '5 minutes');
            INSERT INTO position_record_version
                (tenant_record_id, position_record_version_id, position_record_id,
                 position_status_code, effective_from, recorded_from)
            VALUES ('{tenant}', '10000000-0000-7000-8004-000000000004', '{position}',
                    'open', DATE '2026-09-01', pg_catalog.clock_timestamp() - INTERVAL '5 minutes');
            """,
        )
        assert psql(
            database_url,
            f"SELECT count(*) FROM candidate_worker_conversion_record WHERE tenant_record_id = '{tenant}'::uuid;",
        ) == "0"

        assignment_id = UUID("10000000-0000-7000-8004-000000000005")
        command = acceptance["_assignment_command"](
            assignment_id=assignment_id,
            employment_id=employment,
            person_id=person,
            position_id=position,
            allocation=Decimal("0.5000"),
            suffix=21,
        )
        factory = acceptance["_ConnectionFactory"](
            database_url,
            application_name="orgmetra-assignment-without-conversion",
        )
        result = PostgresPeopleMutationPort(factory).create_assignment(
            command=command,
            authorization=acceptance["_authorization"](assignment_id),
        )
        assert result.assignment_record_id == assignment_id
        assert all(connection.closed for connection in factory.connections)

        state = psql(
            database_url,
            f"""
            SELECT concat_ws('|',
                (SELECT count(*) FROM assignment_record
                 WHERE tenant_record_id = '{tenant}'::uuid
                   AND assignment_record_id = '{assignment_id}'::uuid),
                (SELECT count(*) FROM candidate_worker_conversion_record
                 WHERE tenant_record_id = '{tenant}'::uuid),
                (SELECT count(*) FROM audit_event_record
                 WHERE canonical_event_json::jsonb ->> 'type' = 'orgmetra.people.assignment_created'),
                (SELECT count(*) FROM people_mutation_idempotency_record
                 WHERE tenant_record_id = '{tenant}'::uuid
                   AND command_route = 'assignment-records'));
            """,
        )
        assert state == "1|0|1|1"
