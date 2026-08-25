#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

# This focused security regression intentionally runs after
# test_candidate_application_postgres.sh in Candidate Application Quality. The
# preceding contract owns schema/fixture creation; this test changes only the
# session role/context so it can prove forced RLS as a non-bypass reader rather
# than trusting pg_class metadata alone.
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE orgmetra_candidate_application_reader NOLOGIN NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO orgmetra_candidate_application_reader;
GRANT SELECT ON candidate_application_record TO orgmetra_candidate_application_reader;
GRANT SELECT ON candidate_application_stage_record TO orgmetra_candidate_application_reader;
-- INSERT proves the policies' WITH CHECK path, not only read visibility.
GRANT INSERT ON candidate_application_record TO orgmetra_candidate_application_reader;
GRANT INSERT ON candidate_application_stage_record TO orgmetra_candidate_application_reader;

SET ROLE orgmetra_candidate_application_reader;

DO $$
DECLARE
    application_count bigint;
    stage_count bigint;
BEGIN
    SELECT count(*) INTO application_count FROM candidate_application_record;
    SELECT count(*) INTO stage_count FROM candidate_application_stage_record;

    IF application_count <> 0 OR stage_count <> 0 THEN
        RAISE EXCEPTION
            'missing tenant context exposed candidate application history: applications=%, stages=%',
            application_count,
            stage_count;
    END IF;
END;
$$;

SET orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
DO $$
DECLARE
    application_count bigint;
    stage_count bigint;
BEGIN
    -- Three application rows include the closed bitemporal history row from
    -- the governed-correction regression in the preceding contract; forced RLS
    -- must expose every tenant-local row, history included.
    SELECT count(*) INTO application_count FROM candidate_application_record;
    SELECT count(*) INTO stage_count FROM candidate_application_stage_record;

    IF application_count <> 3 THEN
        RAISE EXCEPTION 'tenant alpha expected 3 applications, got %', application_count;
    END IF;
    IF stage_count <> 3 THEN
        RAISE EXCEPTION 'tenant alpha expected 3 historical stage rows, got %', stage_count;
    END IF;
END;
$$;

SET orgmetra.tenant_record_id = '20000000-0000-7000-8000-000000000001';
DO $$
DECLARE
    application_count bigint;
    stage_count bigint;
BEGIN
    SELECT count(*) INTO application_count FROM candidate_application_record;
    SELECT count(*) INTO stage_count FROM candidate_application_stage_record;

    IF application_count <> 0 OR stage_count <> 0 THEN
        RAISE EXCEPTION
            'tenant beta observed tenant-alpha candidate application history: applications=%, stages=%',
            application_count,
            stage_count;
    END IF;
END;
$$;

RESET ROLE;
SQL

# WITH CHECK isolation: a NOBYPASSRLS role holding INSERT, scoped to tenant
# alpha, must be rejected when it tries to persist a beta-tenant application
# row. Read-only visibility alone never exercises the policies' write path.
set +e
cross_tenant_insert_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
SET ROLE orgmetra_candidate_application_reader;
SET orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
INSERT INTO candidate_application_record (
    tenant_record_id, candidate_application_record_id, candidate_profile_id,
    job_profile_id, position_record_id, requisition_reference, submitted_at,
    recorded_from
) VALUES (
    '20000000-0000-7000-8000-000000000001',
    '30000000-0000-7000-8000-000000000071',
    '20000000-0000-7000-8000-000000000011',
    '20000000-0000-7000-8000-000000000021',
    NULL,
    'requisition:33333333-3333-4333-8333-333333333333',
    TIMESTAMPTZ '2026-08-21 09:15:00+00',
    TIMESTAMPTZ '2026-08-21 09:15:01+00'
);
SQL
} 2>&1)"
cross_tenant_insert_status=$?
set -e
if [[ ${cross_tenant_insert_status} -eq 0 ]]; then
    echo "forced RLS allowed a cross-tenant candidate application insert" >&2
    exit 1
fi
if [[ "${cross_tenant_insert_output}" != *"violates row-level security policy"* ]]; then
    echo "cross-tenant insert failed unexpectedly: ${cross_tenant_insert_output}" >&2
    exit 1
fi

echo "candidate application forced-RLS behavior passed"
