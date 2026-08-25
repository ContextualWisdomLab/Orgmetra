#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

# This focused regression runs after test_candidate_application_postgres.sh in
# Candidate Application Quality. The preceding contract owns schema and fixture
# creation. A candidate application is one durable identity: corrections to its
# Job/Position scope must version the scope without changing the application ID
# that stage history references.
version_relation="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc \
    "SELECT to_regclass('public.candidate_application_record_version')::text;")"
if [[ "${version_relation}" != "candidate_application_record_version" ]]; then
    echo "candidate application scope correction is not separated from the durable anchor" >&2
    exit 1
fi

anchor_recorded_to_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'candidate_application_record'
  AND column_name = 'recorded_to';
")"
if [[ "${anchor_recorded_to_count}" != "0" ]]; then
    echo "durable candidate application anchor still exposes a close-and-replace recorded_to field" >&2
    exit 1
fi

stable_anchor_id="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT candidate_application_record_id
FROM candidate_application_record
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'::uuid
  AND candidate_profile_id = '10000000-0000-7000-8000-000000000011'::uuid
  AND requisition_reference = 'requisition:11111111-1111-4111-8111-111111111111';
")"
if [[ "${stable_anchor_id}" != "10000000-0000-7000-8000-000000000051" ]]; then
    echo "candidate application correction changed the durable application identity" >&2
    exit 1
fi

orphaned_stage_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM candidate_application_stage_record AS stage_record
LEFT JOIN candidate_application_record AS application_record
  ON application_record.tenant_record_id = stage_record.tenant_record_id
 AND application_record.candidate_application_record_id = stage_record.candidate_application_record_id
WHERE application_record.candidate_application_record_id IS NULL;
")"
if [[ "${orphaned_stage_count}" != "0" ]]; then
    echo "candidate application stage history lost its durable application anchor" >&2
    exit 1
fi

# Candidate-specific terminal codes are unsafe without evidence that proves who
# initiated the terminal transition and under which governed boundary. `closed`
# can hide an employer adverse outcome; `withdrawn` can be misused as the same
# shadow outcome unless candidate initiation is authoritatively evidenced.
assert_stage_rejected() {
    local stage_code="$1"
    local stage_record_id="$2"
    local output
    local status

    set +e
    output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO candidate_application_stage_record (
    tenant_record_id, candidate_application_stage_record_id,
    candidate_application_record_id, application_stage_code,
    effective_from, effective_to, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '${stage_record_id}',
    '10000000-0000-7000-8000-000000000052',
    '${stage_code}',
    TIMESTAMPTZ '2026-08-21 11:05:00+00',
    NULL,
    TIMESTAMPTZ '2026-08-21 11:05:01+00'
);
SQL
} 2>&1)"
    status=$?
    set -e

    if [[ ${status} -eq 0 ]]; then
        echo "workflow stage encoded ungoverned candidate-specific terminal outcome: ${stage_code}" >&2
        exit 1
    fi
    if [[ "${output}" != *"candidate_application_stage_code_check"* ]]; then
        echo "${stage_code} application stage failed for an unexpected reason: ${output}" >&2
        exit 1
    fi
}

assert_stage_rejected "closed" "10000000-0000-7000-8000-000000000066"
assert_stage_rejected "withdrawn" "10000000-0000-7000-8000-000000000067"

echo "candidate application decision-boundary contract passed"
