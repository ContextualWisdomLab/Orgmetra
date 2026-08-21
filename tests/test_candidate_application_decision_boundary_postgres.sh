#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

# This focused regression runs after test_candidate_application_postgres.sh in
# Candidate Application Quality. The preceding contract owns schema and fixture
# creation. Candidate-specific terminal codes are unsafe without evidence that
# proves who initiated the terminal transition and under which governed boundary.
# `closed` can hide an employer adverse outcome; `withdrawn` can be misused as the
# same shadow outcome unless candidate initiation is authoritatively evidenced.
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
