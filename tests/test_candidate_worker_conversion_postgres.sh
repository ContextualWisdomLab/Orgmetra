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

set +e
truncate_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
    'TRUNCATE TABLE candidate_worker_conversion_record;' ; } 2>&1)"
truncate_status=$?
set -e
if [[ ${truncate_status} -eq 0 ]]; then
    echo "candidate-worker conversion history was truncatable" >&2
    exit 1
fi
if [[ "${truncate_output}" != *"candidate worker conversion history cannot be truncated"* ]]; then
    echo "conversion TRUNCATE failed for an unexpected reason: ${truncate_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('10000000-0000-7000-8000-000000000001', 'tenant_alpha');

INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000001'
);

INSERT INTO candidate_profile (
    tenant_record_id, candidate_profile_id, application_status_code, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000031',
    'offer', TIMESTAMPTZ '2026-03-01 00:00:00+00'
);
SQL

set +e
legacy_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_worker_link (
    tenant_record_id, candidate_worker_link_id, candidate_profile_id,
    person_record_id, linked_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000033',
    '00000000-0000-7000-8000-000000000031',
    '00000000-0000-7000-8000-000000000001',
    TIMESTAMPTZ '2026-03-02 00:00:00+00'
);
SQL
} 2>&1)"
legacy_status=$?
set -e

if [[ ${legacy_status} -eq 0 ]]; then
    echo "ungoverned legacy candidate-worker link unexpectedly succeeded" >&2
    exit 1
fi
if [[ "${legacy_output}" != *"candidate_worker_link is legacy-only"* ]]; then
    echo "legacy candidate-worker link failed for an unexpected reason: ${legacy_output}" >&2
    exit 1
fi
