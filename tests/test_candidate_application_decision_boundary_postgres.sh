#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

# This focused regression runs after test_candidate_application_postgres.sh in
# Candidate Application Quality. The preceding contract owns schema and fixture
# creation. A generic terminal `closed` stage is not safe because it can encode
# an employer-driven adverse outcome without the authoritative, human-accountable
# selection_decision evidence required for high-impact employment decisions.
set +e
closed_stage_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_application_stage_record (
    tenant_record_id, candidate_application_stage_record_id,
    candidate_application_record_id, application_stage_code,
    effective_from, effective_to, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '10000000-0000-7000-8000-000000000066',
    '10000000-0000-7000-8000-000000000052',
    'closed',
    TIMESTAMPTZ '2026-08-21 11:05:00+00',
    NULL,
    TIMESTAMPTZ '2026-08-21 11:05:01+00'
);
SQL
} 2>&1)"
closed_stage_status=$?
set -e

if [[ ${closed_stage_status} -eq 0 ]]; then
    echo "workflow stage encoded an ambiguous employer-driven terminal outcome outside selection_decision" >&2
    exit 1
fi
if [[ "${closed_stage_output}" != *"candidate_application_stage_code_check"* ]]; then
    echo "closed application stage failed for an unexpected reason: ${closed_stage_output}" >&2
    exit 1
fi

echo "candidate application decision-boundary contract passed"
