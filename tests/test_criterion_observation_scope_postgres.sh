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
    database/migrations/0009_candidate_worker_conversion_governance.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

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
