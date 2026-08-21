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
    SELECT count(*) INTO application_count FROM candidate_application_record;
    SELECT count(*) INTO stage_count FROM candidate_application_stage_record;

    IF application_count <> 2 THEN
        RAISE EXCEPTION 'tenant alpha expected 2 applications, got %', application_count;
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

echo "candidate application forced-RLS behavior passed"
