#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

# Apply the protected-base trigger version, then the sequential upgrade that
# replaces its function without dropping the existing trigger binding.
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
    database/migrations/0014_criterion_observation_chronology.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

trigger_definition="$(psql "${DATABASE_URL}" -Atq -c "
    SELECT pg_catalog.pg_get_triggerdef(oid)
    FROM pg_catalog.pg_trigger
    WHERE tgname = 'criterion_observation_scope_guard'
")"
if [[ "${trigger_definition}" != *"enforce_criterion_observation_scope"* ]]; then
    echo "criterion chronology upgrade replaced the trigger binding unexpectedly" >&2
    exit 1
fi

TENANT_ID="10000000-0000-7000-8000-000000000101"
tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('10000000-0000-7000-8000-000000000101', 'criterion_scope_tenant');

INSERT INTO person_record (
    tenant_record_id, person_record_id, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000102',
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
);

INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000103',
    '10000000-0000-7000-8000-000000000102',
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
);

INSERT INTO employment_record_version (
    tenant_record_id, employment_record_version_id, employment_record_id,
    employment_status_code, employment_concurrency_code,
    effective_from, effective_to, recorded_from
) VALUES
(
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000116',
    '10000000-0000-7000-8000-000000000103',
    'active',
    'exclusive',
    DATE '2026-01-01',
    DATE '2026-11-01',
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
),
(
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000117',
    '10000000-0000-7000-8000-000000000103',
    'terminated',
    'exclusive',
    DATE '2026-11-01',
    NULL,
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
);

INSERT INTO organization_unit (
    tenant_record_id, organization_unit_id, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000104',
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
);

INSERT INTO job_profile (
    tenant_record_id, job_profile_id, recorded_from
) VALUES
(
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000105',
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
),
(
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000106',
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
);

INSERT INTO position_record (
    tenant_record_id, position_record_id, organization_unit_id,
    job_profile_id, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000107',
    '10000000-0000-7000-8000-000000000104',
    '10000000-0000-7000-8000-000000000105',
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
);

INSERT INTO position_record_version (
    tenant_record_id, position_record_version_id, position_record_id,
    position_status_code, effective_from, effective_to, recorded_from
) VALUES
(
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000121',
    '10000000-0000-7000-8000-000000000107',
    'active',
    DATE '2026-01-01',
    DATE '2026-10-01',
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
),
(
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000122',
    '10000000-0000-7000-8000-000000000107',
    'frozen',
    DATE '2026-10-01',
    DATE '2026-11-15',
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
),
(
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000123',
    '10000000-0000-7000-8000-000000000107',
    'active',
    DATE '2026-11-15',
    NULL,
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
);

INSERT INTO assignment_record (
    tenant_record_id, assignment_record_id, employment_record_id,
    person_record_id, position_record_id, allocation_ratio,
    effective_from, effective_to, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000108',
    '10000000-0000-7000-8000-000000000103',
    '10000000-0000-7000-8000-000000000102',
    '10000000-0000-7000-8000-000000000107',
    1.0000,
    DATE '2026-06-01',
    NULL,
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
);

INSERT INTO performance_cycle (
    tenant_record_id, performance_cycle_id, cycle_name, cycle_status_code,
    effective_from, effective_to, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000109',
    '2026 annual performance cycle',
    'cycle_active',
    DATE '2026-01-01',
    DATE '2027-01-01',
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
);

INSERT INTO criterion_blueprint (
    tenant_record_id, criterion_blueprint_id, job_profile_id,
    criterion_type_code, criterion_version_code,
    effective_from, effective_to, recorded_from
) VALUES
(
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000110',
    '10000000-0000-7000-8000-000000000105',
    'job_performance',
    'criterion_v1',
    DATE '2026-01-01',
    NULL,
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
),
(
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000111',
    '10000000-0000-7000-8000-000000000106',
    'job_performance',
    'criterion_v1',
    DATE '2026-01-01',
    NULL,
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
);
SQL

set +e
wrong_job_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO criterion_observation (
    tenant_record_id, criterion_observation_id, criterion_blueprint_id,
    performance_cycle_id, person_record_id, observed_value,
    observed_at, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000112',
    '10000000-0000-7000-8000-000000000111',
    '10000000-0000-7000-8000-000000000109',
    '10000000-0000-7000-8000-000000000102',
    4.2,
    TIMESTAMPTZ '2026-08-15 12:00:00+00',
    TIMESTAMPTZ '2026-08-17 11:30:00+00'
);
SQL
} 2>&1)"
wrong_job_status=$?
set -e
if [[ ${wrong_job_status} -eq 0 ]]; then
    echo "criterion observation accepted a criterion for a job the worker did not hold" >&2
    exit 1
fi
if [[ "${wrong_job_output}" != *"criterion observation does not match an effective worker assignment for the criterion job"* ]]; then
    echo "wrong-job criterion observation failed for an unexpected reason: ${wrong_job_output}" >&2
    exit 1
fi

set +e
pre_assignment_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO criterion_observation (
    tenant_record_id, criterion_observation_id, criterion_blueprint_id,
    performance_cycle_id, person_record_id, observed_value,
    observed_at, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000113',
    '10000000-0000-7000-8000-000000000110',
    '10000000-0000-7000-8000-000000000109',
    '10000000-0000-7000-8000-000000000102',
    3.8,
    TIMESTAMPTZ '2026-05-15 12:00:00+00',
    TIMESTAMPTZ '2026-08-17 11:31:00+00'
);
SQL
} 2>&1)"
pre_assignment_status=$?
set -e
if [[ ${pre_assignment_status} -eq 0 ]]; then
    echo "criterion observation accepted a date before the worker's job assignment" >&2
    exit 1
fi
if [[ "${pre_assignment_output}" != *"criterion observation does not match an effective worker assignment for the criterion job"* ]]; then
    echo "pre-assignment criterion observation failed for an unexpected reason: ${pre_assignment_output}" >&2
    exit 1
fi

set +e
outside_cycle_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO criterion_observation (
    tenant_record_id, criterion_observation_id, criterion_blueprint_id,
    performance_cycle_id, person_record_id, observed_value,
    observed_at, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000114',
    '10000000-0000-7000-8000-000000000110',
    '10000000-0000-7000-8000-000000000109',
    '10000000-0000-7000-8000-000000000102',
    4.5,
    TIMESTAMPTZ '2027-02-15 12:00:00+00',
    TIMESTAMPTZ '2027-02-16 09:00:00+00'
);
SQL
} 2>&1)"
outside_cycle_status=$?
set -e
if [[ ${outside_cycle_status} -eq 0 ]]; then
    echo "criterion observation accepted an observation outside the performance cycle" >&2
    exit 1
fi
if [[ "${outside_cycle_output}" != *"criterion observation is outside the performance cycle effective period"* ]]; then
    echo "out-of-cycle criterion observation failed for an unexpected reason: ${outside_cycle_output}" >&2
    exit 1
fi

set +e
frozen_position_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO criterion_observation (
    tenant_record_id, criterion_observation_id, criterion_blueprint_id,
    performance_cycle_id, person_record_id, observed_value,
    observed_at, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000124',
    '10000000-0000-7000-8000-000000000110',
    '10000000-0000-7000-8000-000000000109',
    '10000000-0000-7000-8000-000000000102',
    4.1,
    TIMESTAMPTZ '2026-10-15 12:00:00+00',
    TIMESTAMPTZ '2026-10-16 09:00:00+00'
);
SQL
} 2>&1)"
frozen_position_status=$?
set -e
if [[ ${frozen_position_status} -eq 0 ]]; then
    echo "criterion observation accepted a worker assignment whose position was not staffable" >&2
    exit 1
fi
if [[ "${frozen_position_output}" != *"criterion observation lacks an assignment with eligible employment and staffable position coverage"* ]]; then
    echo "non-staffable-position criterion observation failed for an unexpected reason: ${frozen_position_output}" >&2
    exit 1
fi

set +e
terminated_employment_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO criterion_observation (
    tenant_record_id, criterion_observation_id, criterion_blueprint_id,
    performance_cycle_id, person_record_id, observed_value,
    observed_at, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000125',
    '10000000-0000-7000-8000-000000000110',
    '10000000-0000-7000-8000-000000000109',
    '10000000-0000-7000-8000-000000000102',
    3.9,
    TIMESTAMPTZ '2026-11-20 12:00:00+00',
    TIMESTAMPTZ '2026-11-21 09:00:00+00'
);
SQL
} 2>&1)"
terminated_employment_status=$?
set -e
if [[ ${terminated_employment_status} -eq 0 ]]; then
    echo "criterion observation accepted a worker assignment after employment termination" >&2
    exit 1
fi
if [[ "${terminated_employment_output}" != *"criterion observation lacks an assignment with eligible employment and staffable position coverage"* ]]; then
    echo "terminated-employment criterion observation failed for an unexpected reason: ${terminated_employment_output}" >&2
    exit 1
fi

set +e
future_observation_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO criterion_observation (
    tenant_record_id, criterion_observation_id, criterion_blueprint_id,
    performance_cycle_id, person_record_id, observed_value,
    observed_at, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000134',
    '10000000-0000-7000-8000-000000000110',
    '10000000-0000-7000-8000-000000000109',
    '10000000-0000-7000-8000-000000000102',
    4.0,
    statement_timestamp() + INTERVAL '1 day',
    statement_timestamp() + INTERVAL '2 days'
);
SQL
} 2>&1)"
future_observation_status=$?
set -e
if [[ ${future_observation_status} -eq 0 ]]; then
    echo "criterion observation accepted timestamps that were both future-dated" >&2
    exit 1
fi
if [[ "${future_observation_output}" != *"criterion observation cannot be observed in the future"* ]]; then
    echo "future-dated criterion observation failed for an unexpected reason: ${future_observation_output}" >&2
    exit 1
fi

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO criterion_observation (
    tenant_record_id, criterion_observation_id, criterion_blueprint_id,
    performance_cycle_id, person_record_id, observed_value,
    observed_at, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000101',
    '10000000-0000-7000-8000-000000000115',
    '10000000-0000-7000-8000-000000000110',
    '10000000-0000-7000-8000-000000000109',
    '10000000-0000-7000-8000-000000000102',
    4.7,
    TIMESTAMPTZ '2026-08-15 12:00:00+00',
    TIMESTAMPTZ '2026-08-17 11:32:00+00'
);
SQL

valid_count="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM criterion_observation
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND criterion_observation_id = '10000000-0000-7000-8000-000000000115'::uuid;
")"
if [[ "${valid_count}" != "1" ]]; then
    echo "valid in-cycle criterion observation for the worker's assigned job was not persisted" >&2
    exit 1
fi

# Fixture rows above stay current-recorded (recorded_to IS NULL). Each closure
# below happens inside an aborting transaction so removing a recorded_to
# predicate from the trigger would admit the observation and fail this contract.
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

expect_recorded_rejection "criterion blueprint recorded-time" "criterion_blueprint" "criterion_blueprint_id" "10000000-0000-7000-8000-000000000110" "10000000-0000-7000-8000-000000000126" "criterion observation references a criterion outside its effective or current-recorded period"
expect_recorded_rejection "performance cycle recorded-time" "performance_cycle" "performance_cycle_id" "10000000-0000-7000-8000-000000000109" "10000000-0000-7000-8000-000000000127" "criterion observation is outside the performance cycle effective period"
expect_recorded_rejection "assignment recorded-time" "assignment_record" "assignment_record_id" "10000000-0000-7000-8000-000000000108" "10000000-0000-7000-8000-000000000128" "criterion observation does not match an effective worker assignment for the criterion job"
expect_recorded_rejection "position anchor recorded-time" "position_record" "position_record_id" "10000000-0000-7000-8000-000000000107" "10000000-0000-7000-8000-000000000129" "criterion observation does not match an effective worker assignment for the criterion job"
expect_recorded_rejection "employment version recorded-time" "employment_record_version" "employment_record_version_id" "10000000-0000-7000-8000-000000000116" "10000000-0000-7000-8000-000000000130" "criterion observation lacks an assignment with eligible employment and staffable position coverage"
expect_recorded_rejection "position version recorded-time" "position_record_version" "position_record_version_id" "10000000-0000-7000-8000-000000000121" "10000000-0000-7000-8000-000000000131" "criterion observation lacks an assignment with eligible employment and staffable position coverage"

# UTC midnight on the assignment start date must be accepted even when the
# session TimeZone is still on the previous local calendar day.
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
    TIMESTAMPTZ '2026-06-01 00:00:00+00',
    TIMESTAMPTZ '2026-08-17 11:41:00+00'
);
SQL

honolulu_midnight_count="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM criterion_observation
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND criterion_observation_id = '10000000-0000-7000-8000-000000000132'::uuid;
")"
if [[ "${honolulu_midnight_count}" != "1" ]]; then
    echo "UTC-midnight assignment-start observation was not persisted under a non-UTC session TimeZone" >&2
    exit 1
fi

# UTC is still May 31 here even though a Tokyo session has crossed into June.
# Accepting this row would mean the trigger used session-local date conversion.
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
    TIMESTAMPTZ '2026-05-31 23:59:59+00',
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
