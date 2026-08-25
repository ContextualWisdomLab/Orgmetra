#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in database/migrations/*.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ALPHA="10000000-0000-7000-8000-000000000001"
TENANT_BETA="20000000-0000-7000-8000-000000000001"
APPLICATION_ONE="10000000-0000-7000-8000-000000000051"
APPLICATION_TWO="10000000-0000-7000-8000-000000000052"

assert_sql_rejected() {
    local expected="$1"
    local description="$2"
    local sql="$3"
    local output
    local status

    set +e
    output="$(printf '%s\n' "${sql}" | psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 2>&1)"
    status=$?
    set -e

    if [[ ${status} -eq 0 ]]; then
        echo "${description}: statement unexpectedly succeeded" >&2
        exit 1
    fi
    if [[ "${output}" != *"${expected}"* ]]; then
        echo "${description}: failed for an unexpected reason: ${output}" >&2
        exit 1
    fi
}

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES
    ('10000000-0000-7000-8000-000000000001', 'tenant_alpha'),
    ('20000000-0000-7000-8000-000000000001', 'tenant_beta');

INSERT INTO candidate_profile (
    tenant_record_id, candidate_profile_id, application_status_code, recorded_from
) VALUES
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000011', 'legacy_unscoped', TIMESTAMPTZ '2026-08-21 09:00:00+00'),
    ('20000000-0000-7000-8000-000000000001', '20000000-0000-7000-8000-000000000011', 'legacy_unscoped', TIMESTAMPTZ '2026-08-21 09:00:00+00');

INSERT INTO job_profile (tenant_record_id, job_profile_id, recorded_from)
VALUES
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000021', TIMESTAMPTZ '2026-08-21 09:00:00+00'),
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000022', TIMESTAMPTZ '2026-08-21 09:00:00+00'),
    ('20000000-0000-7000-8000-000000000001', '20000000-0000-7000-8000-000000000021', TIMESTAMPTZ '2026-08-21 09:00:00+00');

INSERT INTO organization_unit (tenant_record_id, organization_unit_id, recorded_from)
VALUES
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000031', TIMESTAMPTZ '2026-08-21 09:00:00+00'),
    ('20000000-0000-7000-8000-000000000001', '20000000-0000-7000-8000-000000000031', TIMESTAMPTZ '2026-08-21 09:00:00+00');

INSERT INTO position_record (
    tenant_record_id, position_record_id, organization_unit_id, job_profile_id, recorded_from
) VALUES
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000041', '10000000-0000-7000-8000-000000000031', '10000000-0000-7000-8000-000000000021', TIMESTAMPTZ '2026-08-21 09:00:00+00'),
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000042', '10000000-0000-7000-8000-000000000031', '10000000-0000-7000-8000-000000000022', TIMESTAMPTZ '2026-08-21 09:00:00+00');

INSERT INTO candidate_application_record (
    tenant_record_id, candidate_application_record_id, candidate_profile_id,
    requisition_reference, submitted_at, recorded_from
) VALUES
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000051', '10000000-0000-7000-8000-000000000011', 'requisition:11111111-1111-4111-8111-111111111111', TIMESTAMPTZ '2026-08-21 09:10:00+00', TIMESTAMPTZ '2026-08-21 09:10:01+00'),
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000052', '10000000-0000-7000-8000-000000000011', 'requisition:22222222-2222-4222-8222-222222222222', TIMESTAMPTZ '2026-08-21 09:11:00+00', TIMESTAMPTZ '2026-08-21 09:11:01+00');

INSERT INTO candidate_application_record_version (
    tenant_record_id, candidate_application_record_version_id,
    candidate_application_record_id, job_profile_id, position_record_id,
    effective_from, recorded_from
) VALUES
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000071', '10000000-0000-7000-8000-000000000051', '10000000-0000-7000-8000-000000000021', '10000000-0000-7000-8000-000000000041', TIMESTAMPTZ '2026-08-21 09:10:00+00', TIMESTAMPTZ '2026-08-21 09:10:01+00'),
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000072', '10000000-0000-7000-8000-000000000052', '10000000-0000-7000-8000-000000000022', '10000000-0000-7000-8000-000000000042', TIMESTAMPTZ '2026-08-21 09:11:00+00', TIMESTAMPTZ '2026-08-21 09:11:01+00');
SQL

application_count="$(psql "${DATABASE_URL}" -Atqc "SELECT count(*) FROM candidate_application_record WHERE tenant_record_id='${TENANT_ALPHA}'::uuid;")"
if [[ "${application_count}" != "2" ]]; then
    echo "one candidate did not retain two independent application identities" >&2
    exit 1
fi

assert_sql_rejected \
    "candidate_application_candidate_tenant_fk" \
    "cross-tenant candidate anchor" \
    "INSERT INTO candidate_application_record (tenant_record_id,candidate_application_record_id,candidate_profile_id,requisition_reference,submitted_at,recorded_from) VALUES ('${TENANT_ALPHA}'::uuid,'10000000-0000-7000-8000-000000000053'::uuid,'20000000-0000-7000-8000-000000000011'::uuid,'requisition:33333333-3333-4333-8333-333333333333',TIMESTAMPTZ '2026-08-21 09:12:00+00',TIMESTAMPTZ '2026-08-21 09:12:01+00');"

# Keep the mismatch regression outside the current application's effective
# interval so the Position/Job FK is the first causal boundary rather than the
# independent bitemporal-overlap guard.
assert_sql_rejected \
    "candidate_application_version_position_job_tenant_fk" \
    "Position/Job mismatch" \
    "INSERT INTO candidate_application_record_version (tenant_record_id,candidate_application_record_version_id,candidate_application_record_id,job_profile_id,position_record_id,effective_from,effective_to,recorded_from) VALUES ('${TENANT_ALPHA}'::uuid,'10000000-0000-7000-8000-000000000073'::uuid,'${APPLICATION_ONE}'::uuid,'10000000-0000-7000-8000-000000000021'::uuid,'10000000-0000-7000-8000-000000000042'::uuid,TIMESTAMPTZ '2026-08-21 08:00:00+00',TIMESTAMPTZ '2026-08-21 09:00:00+00',TIMESTAMPTZ '2026-08-21 11:00:00+00');"

assert_sql_rejected \
    "candidate_application_candidate_requisition_unique" \
    "duplicate candidate/requisition anchor" \
    "INSERT INTO candidate_application_record (tenant_record_id,candidate_application_record_id,candidate_profile_id,requisition_reference,submitted_at,recorded_from) VALUES ('${TENANT_ALPHA}'::uuid,'10000000-0000-7000-8000-000000000054'::uuid,'10000000-0000-7000-8000-000000000011'::uuid,'requisition:11111111-1111-4111-8111-111111111111',TIMESTAMPTZ '2026-08-21 09:10:00+00',TIMESTAMPTZ '2026-08-21 11:00:00+00');"

assert_sql_rejected \
    "candidate application anchor is immutable" \
    "durable application anchor rewrite" \
    "UPDATE candidate_application_record SET requisition_reference='requisition:99999999-9999-4999-8999-999999999999' WHERE tenant_record_id='${TENANT_ALPHA}'::uuid AND candidate_application_record_id='${APPLICATION_ONE}'::uuid;"

# Correct mutable opening scope by closing one recorded version and appending a
# replacement under the SAME durable application identity.
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE candidate_application_record_version
SET recorded_to = TIMESTAMPTZ '2026-08-21 12:00:00+00'
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'
  AND candidate_application_record_version_id = '10000000-0000-7000-8000-000000000071';

INSERT INTO candidate_application_record_version (
    tenant_record_id, candidate_application_record_version_id,
    candidate_application_record_id, job_profile_id, position_record_id,
    effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '10000000-0000-7000-8000-000000000074',
    '10000000-0000-7000-8000-000000000051',
    '10000000-0000-7000-8000-000000000021',
    '10000000-0000-7000-8000-000000000041',
    TIMESTAMPTZ '2026-08-21 09:10:00+00',
    TIMESTAMPTZ '2026-08-21 12:00:00+00'
);
SQL

open_version_count="$(psql "${DATABASE_URL}" -Atqc "SELECT count(*) FROM candidate_application_record_version WHERE tenant_record_id='${TENANT_ALPHA}'::uuid AND candidate_application_record_id='${APPLICATION_ONE}'::uuid AND recorded_to IS NULL;")"
if [[ "${open_version_count}" != "1" ]]; then
    echo "application scope correction did not leave one open version" >&2
    exit 1
fi

stable_anchor_count="$(psql "${DATABASE_URL}" -Atqc "SELECT count(*) FROM candidate_application_record WHERE tenant_record_id='${TENANT_ALPHA}'::uuid AND candidate_application_record_id='${APPLICATION_ONE}'::uuid;")"
if [[ "${stable_anchor_count}" != "1" ]]; then
    echo "application scope correction changed the durable application anchor" >&2
    exit 1
fi

# A closed correction row that overlaps the old recorded interval must be
# rejected. Adjacent recorded intervals above remain valid.
assert_sql_rejected \
    "candidate_application_version_bitemporal_exclusion" \
    "overlapping application scope history" \
    "INSERT INTO candidate_application_record_version (tenant_record_id,candidate_application_record_version_id,candidate_application_record_id,job_profile_id,position_record_id,effective_from,recorded_from,recorded_to) VALUES ('${TENANT_ALPHA}'::uuid,'10000000-0000-7000-8000-000000000075'::uuid,'${APPLICATION_ONE}'::uuid,'10000000-0000-7000-8000-000000000021'::uuid,'10000000-0000-7000-8000-000000000041'::uuid,TIMESTAMPTZ '2026-08-21 09:10:00+00',TIMESTAMPTZ '2026-08-21 11:00:00+00',TIMESTAMPTZ '2026-08-21 11:30:00+00');"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_application_stage_record (
    tenant_record_id, candidate_application_stage_record_id,
    candidate_application_record_id, application_stage_code,
    effective_from, effective_to, recorded_from
) VALUES
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000061', '10000000-0000-7000-8000-000000000051', 'received', TIMESTAMPTZ '2026-08-21 09:10:00+00', TIMESTAMPTZ '2026-08-21 10:00:00+00', TIMESTAMPTZ '2026-08-21 09:10:01+00'),
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000062', '10000000-0000-7000-8000-000000000051', 'screening', TIMESTAMPTZ '2026-08-21 10:00:00+00', NULL, TIMESTAMPTZ '2026-08-21 10:00:01+00'),
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000068', '10000000-0000-7000-8000-000000000052', 'received', TIMESTAMPTZ '2026-08-21 09:11:00+00', NULL, TIMESTAMPTZ '2026-08-21 09:11:01+00');
SQL

assert_sql_rejected \
    "candidate_application_stage_bitemporal_exclusion" \
    "overlapping stage history" \
    "INSERT INTO candidate_application_stage_record (tenant_record_id,candidate_application_stage_record_id,candidate_application_record_id,application_stage_code,effective_from,effective_to,recorded_from) VALUES ('${TENANT_ALPHA}'::uuid,'10000000-0000-7000-8000-000000000063'::uuid,'${APPLICATION_ONE}'::uuid,'assessment',TIMESTAMPTZ '2026-08-21 09:30:00+00',TIMESTAMPTZ '2026-08-21 10:30:00+00',TIMESTAMPTZ '2026-08-21 11:00:00+00');"

assert_sql_rejected \
    "candidate_application_stage_code_check" \
    "high-impact final outcome stage" \
    "INSERT INTO candidate_application_stage_record (tenant_record_id,candidate_application_stage_record_id,candidate_application_record_id,application_stage_code,effective_from,recorded_from) VALUES ('${TENANT_ALPHA}'::uuid,'10000000-0000-7000-8000-000000000064'::uuid,'${APPLICATION_TWO}'::uuid,'hired',TIMESTAMPTZ '2026-08-21 11:00:00+00',TIMESTAMPTZ '2026-08-21 11:00:01+00');"

assert_sql_rejected \
    "bitemporal correction may only close an open recorded interval" \
    "in-place stage rewrite" \
    "UPDATE candidate_application_stage_record SET application_stage_code='assessment' WHERE tenant_record_id='${TENANT_ALPHA}'::uuid AND candidate_application_stage_record_id='10000000-0000-7000-8000-000000000061'::uuid;"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE candidate_application_stage_record
SET recorded_to = TIMESTAMPTZ '2026-08-21 12:00:00+00'
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'
  AND candidate_application_stage_record_id = '10000000-0000-7000-8000-000000000061';

INSERT INTO candidate_application_stage_record (
    tenant_record_id, candidate_application_stage_record_id,
    candidate_application_record_id, application_stage_code,
    effective_from, effective_to, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '10000000-0000-7000-8000-000000000065',
    '10000000-0000-7000-8000-000000000051',
    'screening',
    TIMESTAMPTZ '2026-08-21 09:10:00+00',
    TIMESTAMPTZ '2026-08-21 10:00:00+00',
    TIMESTAMPTZ '2026-08-21 12:00:00+00'
);
SQL

rls_count="$(psql "${DATABASE_URL}" -Atqc "SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relname IN ('candidate_application_record','candidate_application_record_version','candidate_application_stage_record') AND relrowsecurity AND relforcerowsecurity;")"
if [[ "${rls_count}" != "3" ]]; then
    echo "candidate application relations do not all force row-level security" >&2
    exit 1
fi

assert_sql_rejected \
    "candidate application history cannot be truncated" \
    "stage-history TRUNCATE" \
    "TRUNCATE TABLE candidate_application_stage_record;"
assert_sql_rejected \
    "candidate application history cannot be truncated" \
    "scope-version TRUNCATE" \
    "TRUNCATE TABLE candidate_application_record_version;"

beta_count="$(psql "${DATABASE_URL}" -Atqc "SELECT count(*) FROM tenant_record WHERE tenant_record_id='${TENANT_BETA}'::uuid;")"
if [[ "${beta_count}" != "1" ]]; then
    echo "cross-tenant regression fixture lost the beta tenant" >&2
    exit 1
fi

echo "candidate application PostgreSQL contract passed"
