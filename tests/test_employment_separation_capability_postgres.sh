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
    database/migrations/0015_employment_separation_capability_hardening.sql \
    database/migrations/0016_employment_separation_executor_capability.sql; do
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

capability_role_contract="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT pg_catalog.coalesce(
    pg_catalog.string_agg(
        role.rolname || '|' || role.rolcanlogin::text || '|' || role.rolsuper::text || '|' || role.rolcreatedb::text || '|' || role.rolcreaterole::text || '|' || role.rolreplication::text || '|' || role.rolbypassrls::text,
        E'\\n' ORDER BY role.rolname
    ),
    ''
)
FROM pg_catalog.pg_roles AS role
WHERE role.rolname IN (
    'orgmetra_employment_separation_executor',
    'orgmetra_employment_separation_owner'
);
")"
expected_role_contract=$'orgmetra_employment_separation_executor|false|false|false|false|false|false\norgmetra_employment_separation_owner|false|false|false|false|false|false'
if [[ "${capability_role_contract}" != "${expected_role_contract}" ]]; then
    echo "Employment separation capability roles are absent or over-privileged: ${capability_role_contract}" >&2
    exit 1
fi

function_security_contract="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT function_record.prosecdef::text || '|' || owner_role.rolname
FROM pg_catalog.pg_proc AS function_record
JOIN pg_catalog.pg_roles AS owner_role
  ON owner_role.oid = function_record.proowner
WHERE function_record.oid = 'public.separate_employment_record_once(uuid,uuid,uuid,uuid,date,text,text,text,text,text,text,text,uuid,uuid)'::regprocedure;
")"
if [[ "${function_security_contract}" != "true|orgmetra_employment_separation_owner" ]]; then
    echo "Employment separation function is not owned by the dedicated SECURITY DEFINER authority: ${function_security_contract}" >&2
    exit 1
fi

executor_execute="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT pg_catalog.has_function_privilege(
    'orgmetra_employment_separation_executor',
    'public.separate_employment_record_once(uuid,uuid,uuid,uuid,date,text,text,text,text,text,text,text,uuid,uuid)',
    'EXECUTE'
)::text;
")"
if [[ "${executor_execute}" != "true" ]]; then
    echo "Employment separation executor lacks the reviewed function capability" >&2
    exit 1
fi

executor_direct_dml="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
WITH relation(name) AS (
    VALUES
        ('public.employment_record'),
        ('public.employment_record_version'),
        ('public.assignment_record'),
        ('public.employment_separation_record'),
        ('public.people_mutation_idempotency_record'),
        ('public.audit_event_record'),
        ('public.outbox_delivery_record')
)
SELECT pg_catalog.bool_or(
    pg_catalog.has_table_privilege('orgmetra_employment_separation_executor', name, 'SELECT')
    OR pg_catalog.has_table_privilege('orgmetra_employment_separation_executor', name, 'INSERT')
    OR pg_catalog.has_table_privilege('orgmetra_employment_separation_executor', name, 'UPDATE')
    OR pg_catalog.has_table_privilege('orgmetra_employment_separation_executor', name, 'DELETE')
    OR pg_catalog.has_table_privilege('orgmetra_employment_separation_executor', name, 'TRUNCATE')
)::text
FROM relation;
")"
if [[ "${executor_direct_dml}" != "false" ]]; then
    echo "Employment separation executor unexpectedly has direct HR/audit table DML capability" >&2
    exit 1
fi

set +e
executor_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
SET ROLE orgmetra_employment_separation_executor;
SET orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
SELECT *
FROM public.separate_employment_record_once(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000101'::uuid,
    '00000000-0000-7000-8000-000000000201'::uuid,
    DATE '2026-06-01',
    'voluntary_resignation',
    'separation_packet:executor_probe',
    'v1',
    'keyverse_subject:executor_probe',
    'workforce_admin',
    'human_confirmation:executor_probe',
    'employment-separation-executor-probe',
    '00000000-0000-4000-8000-000000000501'::uuid,
    '00000000-0000-4000-8000-000000000601'::uuid
);
SQL
} 2>&1)"
executor_status=$?
set -e
if [[ ${executor_status} -eq 0 ]]; then
    echo "executor probe unexpectedly found a target Employment" >&2
    exit 1
fi
if [[ "${executor_output}" != *"employment separation target does not match tenant person and employment"* ]]; then
    echo "executor did not cross the reviewed function boundary with deny-default table privileges: ${executor_output}" >&2
    exit 1
fi

probe_suffix="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "SELECT substr(replace(gen_random_uuid()::text, '-', ''), 1, 24);")"
if [[ ! "${probe_suffix}" =~ ^[0-9a-f]{24}$ ]]; then
    echo "failed to generate collision-resistant Employment separation probe identity" >&2
    exit 1
fi
probe_role="orgmetra_employment_separation_probe_${probe_suffix}"
probe_role_created=false

cleanup_probe_role_best_effort() {
    if [[ "${probe_role_created}" != "true" ]]; then
        return
    fi
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v probe_role="${probe_role}" >/dev/null 2>&1 <<'SQL' || true
DROP OWNED BY :"probe_role";
DROP ROLE :"probe_role";
SQL
}
trap cleanup_probe_role_best_effort EXIT

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v probe_role="${probe_role}" <<'SQL'
CREATE ROLE :"probe_role"
    NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOBYPASSRLS;
SQL
probe_role_created=true

set +e
probe_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v probe_role="${probe_role}" <<'SQL'
SET ROLE :"probe_role";
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

if ! psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v probe_role="${probe_role}" <<'SQL'
DROP OWNED BY :"probe_role";
DROP ROLE :"probe_role";
SQL
then
    echo "failed to clean Employment separation probe role after successful acceptance path" >&2
    exit 1
fi
probe_role_created=false
trap - EXIT

if [[ ${probe_status} -eq 0 ]]; then
    echo "ungranted probe role unexpectedly executed Employment separation" >&2
    exit 1
fi
if [[ "${probe_output}" != *"permission denied for function separate_employment_record_once"* ]]; then
    echo "probe role failed for an unexpected reason: ${probe_output}" >&2
    exit 1
fi

echo "PostgreSQL Employment separation capability contract passed"
