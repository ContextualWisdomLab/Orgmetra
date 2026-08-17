#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
TENANT_ID="10000000-0000-7000-8000-000000000101"

tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

expect_recorded_rejection() {
    local label="$1" table_name="$2" id_column="$3" record_id="$4" observation_id="$5" expected_message="$6"
    local output status
    set +e
    output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
BEGIN;
UPDATE ${table_name}
SET recorded_to = TIMESTAMPTZ '2026-08-17 00:00:00+00'
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND ${id_column} = '${record_id}'::uuid;
INSERT INTO criterion_observation (
    tenant_record_id, criterion_observation_id, criterion_blueprint_id,
    performance_cycle_id, person_record_id, observed_value, observed_at, recorded_from
) VALUES (
    '${TENANT_ID}', '${observation_id}',
    '10000000-0000-7000-8000-000000000110',
    '10000000-0000-7000-8000-000000000109',
    '10000000-0000-7000-8000-000000000102', 4.4,
    TIMESTAMPTZ '2026-08-15 12:00:00+00',
    TIMESTAMPTZ '2026-08-17 11:40:00+00'
);
ROLLBACK;
SQL
} 2>&1)"
    status=$?
    set -e
    if [[ ${status} -eq 0 ]]; then
        echo "${label}: criterion observation accepted a system-closed record" >&2
        exit 1
    fi
    if [[ "${output}" != *"${expected_message}"* ]]; then
        echo "${label}: closed-record rejection failed unexpectedly: ${output}" >&2
        exit 1
    fi
}

# The parent scope test creates the current-recorded fixture. Each closure occurs
# in an aborting transaction so every recorded-time predicate is isolated.
expect_recorded_rejection "criterion blueprint recorded-time" "criterion_blueprint" "criterion_blueprint_id" "10000000-0000-7000-8000-000000000110" "10000000-0000-7000-8000-000000000126" "criterion observation references a criterion outside its effective or current-recorded period"
expect_recorded_rejection "performance cycle recorded-time" "performance_cycle" "performance_cycle_id" "10000000-0000-7000-8000-000000000109" "10000000-0000-7000-8000-000000000127" "criterion observation is outside the performance cycle effective period"
expect_recorded_rejection "assignment recorded-time" "assignment_record" "assignment_record_id" "10000000-0000-7000-8000-000000000108" "10000000-0000-7000-8000-000000000128" "criterion observation does not match an effective worker assignment for the criterion job"
expect_recorded_rejection "position anchor recorded-time" "position_record" "position_record_id" "10000000-0000-7000-8000-000000000107" "10000000-0000-7000-8000-000000000129" "criterion observation does not match an effective worker assignment for the criterion job"
expect_recorded_rejection "employment version recorded-time" "employment_record_version" "employment_record_version_id" "10000000-0000-7000-8000-000000000116" "10000000-0000-7000-8000-000000000130" "criterion observation lacks an assignment with eligible employment and staffable position coverage"
expect_recorded_rejection "position version recorded-time" "position_record_version" "position_record_version_id" "10000000-0000-7000-8000-000000000121" "10000000-0000-7000-8000-000000000131" "criterion observation lacks an assignment with eligible employment and staffable position coverage"

# UTC June 1 has assignment coverage even while Honolulu is still on May 31.
tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
SET TIME ZONE 'Pacific/Honolulu';
INSERT INTO criterion_observation (
    tenant_record_id, criterion_observation_id, criterion_blueprint_id,
    performance_cycle_id, person_record_id, observed_value, observed_at, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000132',
    '10000000-0000-7000-8000-000000000110',
    '10000000-0000-7000-8000-000000000109',
    '10000000-0000-7000-8000-000000000102', 4.6,
    TIMESTAMPTZ '2026-06-01 00:30:00+00',
    TIMESTAMPTZ '2026-08-17 11:41:00+00'
);
SQL

# UTC is still May 31 here even though a Tokyo session has crossed into June.
set +e
utc_boundary_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
SET TIME ZONE 'Asia/Tokyo';
INSERT INTO criterion_observation (
    tenant_record_id, criterion_observation_id, criterion_blueprint_id,
    performance_cycle_id, person_record_id, observed_value, observed_at, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000133',
    '10000000-0000-7000-8000-000000000110',
    '10000000-0000-7000-8000-000000000109',
    '10000000-0000-7000-8000-000000000102', 4.3,
    TIMESTAMPTZ '2026-05-31 23:30:00+00',
    TIMESTAMPTZ '2026-08-17 11:42:00+00'
);
SQL
} 2>&1)"
utc_boundary_status=$?
set -e
if [[ ${utc_boundary_status} -eq 0 ]]; then
    echo "UTC-boundary observation used a session-local June date" >&2
    exit 1
fi
if [[ "${utc_boundary_output}" != *"criterion observation does not match an effective worker assignment for the criterion job"* ]]; then
    echo "UTC-boundary observation failed unexpectedly: ${utc_boundary_output}" >&2
    exit 1
fi
