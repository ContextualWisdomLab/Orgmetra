#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('10000000-0000-7000-8000-000000000001', 'tenant_alpha');

INSERT INTO candidate_profile (
    tenant_record_id, candidate_profile_id, application_status_code
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000021',
    'active'
);

INSERT INTO job_profile (tenant_record_id, job_profile_id)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000022'
);

BEGIN;
INSERT INTO decision_evidence_set (
    tenant_record_id,
    decision_evidence_set_id,
    evidence_set_version_code,
    digest_algorithm_code,
    evidence_set_digest
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000023',
    'v1',
    'sha256',
    repeat('a', 64)
);
INSERT INTO selection_decision_evidence (
    tenant_record_id,
    selection_decision_evidence_id,
    decision_evidence_set_id,
    evidence_reference,
    evidence_version_code
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000024',
    '00000000-0000-7000-8000-000000000023',
    'evidence://interview/42',
    '2026-08-16'
);
INSERT INTO selection_decision (
    tenant_record_id,
    selection_decision_id,
    candidate_profile_id,
    job_profile_id,
    decision_evidence_set_id,
    actor_reference,
    purpose_code,
    decision_code,
    decision_reason,
    confirmation_reference,
    decided_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000025',
    '00000000-0000-7000-8000-000000000021',
    '00000000-0000-7000-8000-000000000022',
    '00000000-0000-7000-8000-000000000023',
    'actor://hr/7',
    'selection_review',
    'advance',
    'Human reviewer confirmed the versioned evidence set.',
    'confirmation://workflow/99',
    TIMESTAMPTZ '2026-08-16 10:00:00+00'
);
COMMIT;
SQL

set +e
late_insert_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO selection_decision_evidence (
    tenant_record_id,
    selection_decision_evidence_id,
    decision_evidence_set_id,
    evidence_reference,
    evidence_version_code
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000026',
    '00000000-0000-7000-8000-000000000023',
    'evidence://late/forbidden',
    '2026-08-16'
);
SQL
} 2>&1)"
late_insert_status=$?
set -e
if [[ ${late_insert_status} -eq 0 ]]; then
    echo "sealed decision evidence set accepted a late evidence member" >&2
    exit 1
fi
if [[ "${late_insert_output}" != *"sealed evidence set cannot accept new members"* ]]; then
    echo "late evidence insert failed for an unexpected reason: ${late_insert_output}" >&2
    exit 1
fi

set +e
reuse_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO selection_decision (
    tenant_record_id,
    selection_decision_id,
    candidate_profile_id,
    job_profile_id,
    decision_evidence_set_id,
    actor_reference,
    purpose_code,
    decision_code,
    decision_reason,
    confirmation_reference,
    decided_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000027',
    '00000000-0000-7000-8000-000000000021',
    '00000000-0000-7000-8000-000000000022',
    '00000000-0000-7000-8000-000000000023',
    'actor://hr/8',
    'selection_review',
    'reject',
    'A second decision must not reuse a sealed evidence set.',
    'confirmation://workflow/100',
    TIMESTAMPTZ '2026-08-16 10:01:00+00'
);
SQL
} 2>&1)"
reuse_status=$?
set -e
if [[ ${reuse_status} -eq 0 ]]; then
    echo "one sealed evidence set was reused by multiple decisions" >&2
    exit 1
fi
if [[ "${reuse_output}" != *"evidence set is already sealed by a decision"* ]]; then
    echo "evidence-set reuse failed for an unexpected reason: ${reuse_output}" >&2
    exit 1
fi

echo "PostgreSQL decision-evidence sealing contract passed"
