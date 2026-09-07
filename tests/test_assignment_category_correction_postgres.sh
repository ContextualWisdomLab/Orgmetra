#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0017_assignment_category_code.sql

# A late migration failure must roll back the relation and all dependent DDL.
# Colliding with the trigger function fails after CREATE TABLE has executed,
# proving that BEGIN/COMMIT is the recovery boundary rather than psql autocommit.
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE FUNCTION public.enforce_assignment_supersession_link()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN NEW;
END;
$$;
SQL

set +e
atomicity_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0018_assignment_category_supersession.sql 2>&1)"
atomicity_status=$?
set -e
if [[ ${atomicity_status} -eq 0 || "${atomicity_output}" != *"enforce_assignment_supersession_link"* ]]; then
    echo "assignment supersession migration did not hit the deterministic late conflict: ${atomicity_output}" >&2
    exit 1
fi

partial_table="$(psql "${DATABASE_URL}" -Atqc "SELECT pg_catalog.to_regclass('public.assignment_supersession_record') IS NOT NULL;")"
if [[ "${partial_table}" != "f" ]]; then
    echo "failed assignment supersession migration left partial schema state" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "DROP FUNCTION public.enforce_assignment_supersession_link();"
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0018_assignment_category_supersession.sql

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES
    ('10000000-0000-7000-8000-000000000001', 'tenant_alpha'),
    ('20000000-0000-7000-8000-000000000001', 'tenant_beta');
INSERT INTO person_record (tenant_record_id, person_record_id, recorded_from)
VALUES ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000101', TIMESTAMPTZ '2026-09-03 00:00:00+00');
INSERT INTO employment_record (tenant_record_id, employment_record_id, person_record_id, recorded_from)
VALUES ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000111', '10000000-0000-7000-8000-000000000101', TIMESTAMPTZ '2026-09-03 00:00:00+00');
INSERT INTO organization_unit (tenant_record_id, organization_unit_id, recorded_from)
VALUES ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000121', TIMESTAMPTZ '2026-09-03 00:00:00+00');
INSERT INTO job_profile (tenant_record_id, job_profile_id, recorded_from)
VALUES ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000131', TIMESTAMPTZ '2026-09-03 00:00:00+00');
INSERT INTO position_record (
    tenant_record_id, position_record_id, organization_unit_id, job_profile_id, recorded_from
) VALUES
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000141', '10000000-0000-7000-8000-000000000121', '10000000-0000-7000-8000-000000000131', TIMESTAMPTZ '2026-09-03 00:00:00+00'),
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000142', '10000000-0000-7000-8000-000000000121', '10000000-0000-7000-8000-000000000131', TIMESTAMPTZ '2026-09-03 00:00:00+00');

INSERT INTO assignment_record (
    tenant_record_id, assignment_record_id, employment_record_id, person_record_id,
    position_record_id, allocation_ratio, assignment_category_code,
    effective_from, effective_to, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000151',
    '10000000-0000-7000-8000-000000000111', '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000141', 0.5000, 'primary',
    DATE '2026-09-03', DATE '2026-10-01', TIMESTAMPTZ '2026-09-03 00:01:00+00'
);
UPDATE assignment_record
SET recorded_to = TIMESTAMPTZ '2026-09-03 00:02:00+00'
WHERE assignment_record_id = '10000000-0000-7000-8000-000000000151';

INSERT INTO assignment_record (
    tenant_record_id, assignment_record_id, employment_record_id, person_record_id,
    position_record_id, allocation_ratio, assignment_category_code,
    effective_from, effective_to, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000152',
    '10000000-0000-7000-8000-000000000111', '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000141', 0.5000, 'concurrent_secondary',
    DATE '2026-09-03', DATE '2026-10-01', TIMESTAMPTZ '2026-09-03 00:02:00+00'
);

INSERT INTO assignment_supersession_record (
    tenant_record_id,
    assignment_supersession_record_id,
    predecessor_assignment_record_id,
    replacement_assignment_record_id,
    recorded_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '10000000-0000-7000-8000-000000000190',
    '10000000-0000-7000-8000-000000000151',
    '10000000-0000-7000-8000-000000000152',
    TIMESTAMPTZ '2026-09-03 00:02:00+00'
);
SQL

edge_count="$(psql "${DATABASE_URL}" -Atqc "SELECT count(*) FROM assignment_supersession_record WHERE tenant_record_id='10000000-0000-7000-8000-000000000001' AND predecessor_assignment_record_id='10000000-0000-7000-8000-000000000151' AND replacement_assignment_record_id='10000000-0000-7000-8000-000000000152' AND recorded_at=TIMESTAMPTZ '2026-09-03 00:02:00+00';")"
test "${edge_count}" = "1"

rls_state="$(psql "${DATABASE_URL}" -Atqc "SELECT relrowsecurity::text || ':' || relforcerowsecurity::text FROM pg_class WHERE oid='public.assignment_supersession_record'::regclass;")"
test "${rls_state}" = "true:true"

policy_count="$(psql "${DATABASE_URL}" -Atqc "SELECT count(*) FROM pg_policy WHERE polrelid='public.assignment_supersession_record'::regclass AND polname='assignment_supersession_scope_policy';")"
test "${policy_count}" = "1"

# RLS catalog flags are insufficient evidence. Prove visibility through an
# ordinary NOBYPASSRLS role with absent, matching, and non-matching tenant context.
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE orgmetra_assignment_correction_reader NOLOGIN NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO orgmetra_assignment_correction_reader;
GRANT SELECT ON public.assignment_supersession_record TO orgmetra_assignment_correction_reader;
GRANT EXECUTE ON FUNCTION public.current_tenant_record_id() TO orgmetra_assignment_correction_reader;
SET ROLE orgmetra_assignment_correction_reader;

RESET orgmetra.tenant_record_id;
DO $$
BEGIN
    IF (SELECT count(*) FROM public.assignment_supersession_record) <> 0 THEN
        RAISE EXCEPTION 'missing tenant context exposed assignment supersession provenance';
    END IF;
END;
$$;

SET orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
DO $$
BEGIN
    IF (SELECT count(*) FROM public.assignment_supersession_record) <> 1 THEN
        RAISE EXCEPTION 'tenant alpha could not read its assignment supersession provenance';
    END IF;
END;
$$;

SET orgmetra.tenant_record_id = '20000000-0000-7000-8000-000000000001';
DO $$
BEGIN
    IF (SELECT count(*) FROM public.assignment_supersession_record) <> 0 THEN
        RAISE EXCEPTION 'tenant beta observed tenant alpha assignment supersession provenance';
    END IF;
END;
$$;
RESET ROLE;
SQL

set +e
update_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "UPDATE assignment_supersession_record SET recorded_at=TIMESTAMPTZ '2026-09-03 00:03:00+00' WHERE assignment_supersession_record_id='10000000-0000-7000-8000-000000000190';" 2>&1)"
update_status=$?
set -e
if [[ ${update_status} -eq 0 || "${update_output}" != *"append-only"* ]]; then
    echo "assignment supersession provenance was mutable: ${update_output}" >&2
    exit 1
fi

set +e
truncate_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "TRUNCATE assignment_supersession_record;" 2>&1)"
truncate_status=$?
set -e
if [[ ${truncate_status} -eq 0 || "${truncate_output}" != *"cannot be truncated"* ]]; then
    echo "assignment supersession provenance could be truncated: ${truncate_output}" >&2
    exit 1
fi

set +e
sentinel_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "INSERT INTO assignment_supersession_record (tenant_record_id, assignment_supersession_record_id, predecessor_assignment_record_id, replacement_assignment_record_id, recorded_at) VALUES ('10000000-0000-7000-8000-000000000001','00000000-0000-0000-0000-000000000000','10000000-0000-7000-8000-000000000151','10000000-0000-7000-8000-000000000152',TIMESTAMPTZ '2026-09-03 00:02:00+00');" 2>&1)"
sentinel_status=$?
set -e
if [[ ${sentinel_status} -eq 0 || "${sentinel_output}" != *"assignment_supersession_record_id_operational_check"* ]]; then
    echo "reserved supersession identity escaped validation: ${sentinel_output}" >&2
    exit 1
fi

# Trigger-level linkage validation must fail before uniqueness could otherwise
# hide a malformed second edge from the same predecessor.
set +e
time_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "INSERT INTO assignment_supersession_record (tenant_record_id, assignment_supersession_record_id, predecessor_assignment_record_id, replacement_assignment_record_id, recorded_at) VALUES ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000191','10000000-0000-7000-8000-000000000151','10000000-0000-7000-8000-000000000152',TIMESTAMPTZ '2026-09-03 00:03:00+00');" 2>&1)"
time_status=$?
set -e
if [[ ${time_status} -eq 0 || "${time_output}" != *"recorded timestamp"* ]]; then
    echo "mismatched supersession time escaped linkage validation: ${time_output}" >&2
    exit 1
fi

# A replacement with changed business truth is not a category correction.
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO assignment_record (
    tenant_record_id, assignment_record_id, employment_record_id, person_record_id,
    position_record_id, allocation_ratio, assignment_category_code,
    effective_from, effective_to, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000153',
    '10000000-0000-7000-8000-000000000111', '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000142', 0.5000, 'concurrent_secondary',
    DATE '2026-09-03', DATE '2026-10-01', TIMESTAMPTZ '2026-09-03 00:02:00+00'
);
SQL

set +e
business_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "INSERT INTO assignment_supersession_record (tenant_record_id, assignment_supersession_record_id, predecessor_assignment_record_id, replacement_assignment_record_id, recorded_at) VALUES ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000192','10000000-0000-7000-8000-000000000151','10000000-0000-7000-8000-000000000153',TIMESTAMPTZ '2026-09-03 00:02:00+00');" 2>&1)"
business_status=$?
set -e
if [[ ${business_status} -eq 0 || "${business_output}" != *"business truth"* ]]; then
    echo "non-category replacement escaped supersession validation: ${business_output}" >&2
    exit 1
fi

# Same-category replacement is also invalid even when every other fact matches.
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO assignment_record (
    tenant_record_id, assignment_record_id, employment_record_id, person_record_id,
    position_record_id, allocation_ratio, assignment_category_code,
    effective_from, effective_to, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000154',
    '10000000-0000-7000-8000-000000000111', '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000141', 0.5000, 'primary',
    DATE '2026-09-03', DATE '2026-10-01', TIMESTAMPTZ '2026-09-03 00:02:00+00'
);
SQL

set +e
category_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "INSERT INTO assignment_supersession_record (tenant_record_id, assignment_supersession_record_id, predecessor_assignment_record_id, replacement_assignment_record_id, recorded_at) VALUES ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000194','10000000-0000-7000-8000-000000000151','10000000-0000-7000-8000-000000000154',TIMESTAMPTZ '2026-09-03 00:02:00+00');" 2>&1)"
category_status=$?
set -e
if [[ ${category_status} -eq 0 || "${category_output}" != *"must change one explicit assignment category"* ]]; then
    echo "same-category replacement escaped supersession validation: ${category_output}" >&2
    exit 1
fi

# The normalized edge is one-to-one: a predecessor cannot fork and a replacement
# cannot claim multiple predecessors.
set +e
duplicate_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "INSERT INTO assignment_supersession_record (tenant_record_id, assignment_supersession_record_id, predecessor_assignment_record_id, replacement_assignment_record_id, recorded_at) VALUES ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000193','10000000-0000-7000-8000-000000000151','10000000-0000-7000-8000-000000000152',TIMESTAMPTZ '2026-09-03 00:02:00+00');" 2>&1)"
duplicate_status=$?
set -e
if [[ ${duplicate_status} -eq 0 || "${duplicate_output}" != *"assignment_supersession_predecessor_unique"* ]]; then
    echo "predecessor supersession fork escaped uniqueness: ${duplicate_output}" >&2
    exit 1
fi

echo "assignment category correction PostgreSQL provenance contract passed"
