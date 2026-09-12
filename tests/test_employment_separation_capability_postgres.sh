#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0003_audit_outbox_persistence.sql \
    database/migrations/0004_outbox_delivery_claim.sql \
    database/migrations/0005_outbox_delivery_finalization.sql \
    database/migrations/0006_outbox_delivery_dead_letter.sql \
    database/migrations/0007_outbox_retry_exhaustion.sql \
    database/migrations/0008_audit_outbox_review_hardening.sql \
    database/migrations/0009_candidate_worker_conversion_governance.sql \
    database/migrations/0010_validity_study_case_integrity.sql \
    database/migrations/0011_criterion_observation_scope.sql \
    database/migrations/0012_people_mutation_idempotency.sql \
    database/migrations/0013_job_analysis_snapshot.sql \
    database/migrations/0014_employment_separation_transition.sql \
    database/migrations/0015_employment_separation_capability_hardening.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

public_execute_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_catalog.pg_proc AS function_record
CROSS JOIN LATERAL pg_catalog.aclexplode(
    COALESCE(
        function_record.proacl,
        pg_catalog.acldefault('f', function_record.proowner)
    )
) AS function_acl
WHERE function_record.oid = 'public.separate_employment_record_once(uuid,uuid,uuid,uuid,date,text,text,text,text,text,text,text,uuid,uuid)'::regprocedure
  AND function_acl.grantee = 0
  AND function_acl.privilege_type = 'EXECUTE';
")"
if [[ "${public_execute_count}" != "0" ]]; then
    echo "PUBLIC unexpectedly retains Employment separation EXECUTE capability" >&2
    exit 1
fi

trigger_execute_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_catalog.pg_proc AS function_record
CROSS JOIN LATERAL pg_catalog.aclexplode(
    COALESCE(
        function_record.proacl,
        pg_catalog.acldefault('f', function_record.proowner)
    )
) AS function_acl
WHERE function_record.oid = 'public.reject_employment_separation_truncate()'::regprocedure
  AND function_acl.grantee = 0
  AND function_acl.privilege_type = 'EXECUTE';
")"
if [[ "${trigger_execute_count}" != "0" ]]; then
    echo "PUBLIC unexpectedly retains Employment separation trigger EXECUTE capability" >&2
    exit 1
fi

security_invoker="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT (NOT prosecdef)::text
FROM pg_catalog.pg_proc
WHERE oid = 'public.separate_employment_record_once(uuid,uuid,uuid,uuid,date,text,text,text,text,text,text,text,uuid,uuid)'::regprocedure;
")"
if [[ "${security_invoker}" != "true" ]]; then
    echo "Employment separation function unexpectedly runs as SECURITY DEFINER" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE orgmetra_employment_separation_probe
    NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOBYPASSRLS;
SQL

set +e
probe_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
SET ROLE orgmetra_employment_separation_probe;
SET orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
SELECT *
FROM public.separate_employment_record_once(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000101'::uuid,
    '00000000-0000-7000-8000-000000000201'::uuid,
    DATE '2026-06-01',
    'voluntary_resignation',
    'separation_packet:probe',
    'v1',
    'keyverse_subject:probe',
    'workforce_admin',
    'human_confirmation:probe',
    'employment-separation-probe-key',
    '00000000-0000-4000-8000-000000000501'::uuid,
    '00000000-0000-4000-8000-000000000601'::uuid
);
SQL
} 2>&1)"
probe_status=$?
set -e

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
DROP ROLE orgmetra_employment_separation_probe;
SQL

if [[ ${probe_status} -eq 0 ]]; then
    echo "ungranted probe role unexpectedly executed Employment separation" >&2
    exit 1
fi
if [[ "${probe_output}" != *"permission denied for function separate_employment_record_once"* ]]; then
    echo "probe role failed for an unexpected reason: ${probe_output}" >&2
    exit 1
fi

echo "PostgreSQL Employment separation capability contract passed"
