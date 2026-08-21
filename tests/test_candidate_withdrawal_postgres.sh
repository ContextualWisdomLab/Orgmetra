#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in database/migrations/*.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES
    ('10000000-0000-7000-8000-000000000001', 'tenant_alpha'),
    ('20000000-0000-7000-8000-000000000001', 'tenant_beta');

INSERT INTO candidate_profile (
    tenant_record_id, candidate_profile_id, application_status_code, recorded_from
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000011',
        'legacy_unscoped',
        TIMESTAMPTZ '2026-08-21 09:00:00+00'
    ),
    (
        '20000000-0000-7000-8000-000000000001',
        '20000000-0000-7000-8000-000000000011',
        'legacy_unscoped',
        TIMESTAMPTZ '2026-08-21 09:00:00+00'
    );

INSERT INTO job_profile (tenant_record_id, job_profile_id, recorded_from)
VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000021',
        TIMESTAMPTZ '2026-08-21 09:00:00+00'
    ),
    (
        '20000000-0000-7000-8000-000000000001',
        '20000000-0000-7000-8000-000000000021',
        TIMESTAMPTZ '2026-08-21 09:00:00+00'
    );

INSERT INTO candidate_application_record (
    tenant_record_id, candidate_application_record_id, candidate_profile_id,
    job_profile_id, requisition_reference, submitted_at, recorded_from
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000051',
        '10000000-0000-7000-8000-000000000011',
        '10000000-0000-7000-8000-000000000021',
        'requisition:11111111-1111-4111-8111-111111111111',
        TIMESTAMPTZ '2026-08-21 09:10:00+00',
        TIMESTAMPTZ '2026-08-21 09:10:01+00'
    ),
    (
        '20000000-0000-7000-8000-000000000001',
        '20000000-0000-7000-8000-000000000051',
        '20000000-0000-7000-8000-000000000011',
        '20000000-0000-7000-8000-000000000021',
        'requisition:22222222-2222-4222-8222-222222222222',
        TIMESTAMPTZ '2026-08-21 09:10:00+00',
        TIMESTAMPTZ '2026-08-21 09:10:01+00'
    );
SQL

record_event() {
    local event_id="$1"
    local outbox_id="$2"
    local tenant_id="$3"
    local subject="$4"
    local actor="$5"
    local evidence="$6"
    local event_time="$7"

    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
        --set=event_id="${event_id}" \
        --set=outbox_id="${outbox_id}" \
        --set=tenant_id="${tenant_id}" \
        --set=subject="${subject}" \
        --set=actor="${actor}" \
        --set=evidence="${evidence}" \
        --set=event_time="${event_time}" <<'SQL'
WITH envelope AS (
    SELECT jsonb_build_object(
        'specversion', '1.0',
        'id', :'event_id',
        'source', 'urn:orgmetra:talent_acquisition',
        'type', 'orgmetra.candidate.application_withdrawn',
        'subject', :'subject',
        'time', :'event_time',
        'datacontenttype', 'application/json',
        'orgmetratenant', :'tenant_id',
        'orgmetraactor', :'actor',
        'orgmetrapurpose', 'candidate_withdrawal',
        'orgmetrareason', 'candidate_requested',
        'orgmetraevidence', :'evidence',
        'data', jsonb_build_object(
            'high_impact', false,
            'result_code', 'application_withdrawn'
        )
    )::text AS canonical_event_json
), payload AS (
    SELECT
        canonical_event_json,
        encode(digest(convert_to(canonical_event_json, 'UTF8'), 'sha256'), 'hex')
            AS event_digest
    FROM envelope
)
SELECT record_audit_outbox_event(
    :'tenant_id'::uuid,
    :'event_id'::uuid,
    :'outbox_id'::uuid,
    canonical_event_json,
    event_digest,
    'talent_acquisition_events'
)
FROM payload;
SQL
}

record_event \
    '70000000-0000-7000-8000-000000000001' \
    '71000000-0000-7000-8000-000000000001' \
    '10000000-0000-7000-8000-000000000001' \
    'candidate_withdrawal_record:72000000-0000-7000-8000-000000000001' \
    'candidate:73000000-0000-4000-8000-000000000001' \
    'candidate_withdrawal_evidence:74000000-0000-4000-8000-000000000001' \
    '2026-08-21T09:20:00Z'

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_withdrawal_record (
    tenant_record_id,
    candidate_withdrawal_record_id,
    candidate_application_record_id,
    initiating_actor_reference,
    identity_resolution_reference,
    identity_resolution_digest,
    withdrawal_evidence_reference,
    withdrawal_evidence_digest,
    evidence_version,
    withdrawn_at,
    audit_event_record_id,
    recorded_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '72000000-0000-7000-8000-000000000001',
    '10000000-0000-7000-8000-000000000051',
    'candidate:73000000-0000-4000-8000-000000000001',
    'identity_resolution:75000000-0000-4000-8000-000000000001',
    repeat('a', 64),
    'candidate_withdrawal_evidence:74000000-0000-4000-8000-000000000001',
    repeat('b', 64),
    1,
    TIMESTAMPTZ '2026-08-21 09:20:00+00',
    '70000000-0000-7000-8000-000000000001',
    TIMESTAMPTZ '2026-08-21 09:20:01+00'
);
SQL

persisted_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM candidate_withdrawal_record
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'::uuid
  AND candidate_application_record_id = '10000000-0000-7000-8000-000000000051'::uuid;
")"
if [[ "${persisted_count}" != "1" ]]; then
    echo "governed candidate withdrawal was not persisted exactly once" >&2
    exit 1
fi

set +e
duplicate_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_withdrawal_record (
    tenant_record_id, candidate_withdrawal_record_id,
    candidate_application_record_id, initiating_actor_reference,
    identity_resolution_reference, identity_resolution_digest,
    withdrawal_evidence_reference, withdrawal_evidence_digest,
    evidence_version, withdrawn_at, audit_event_record_id, recorded_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '72000000-0000-7000-8000-000000000002',
    '10000000-0000-7000-8000-000000000051',
    'candidate:73000000-0000-4000-8000-000000000001',
    'identity_resolution:75000000-0000-4000-8000-000000000001',
    repeat('a', 64),
    'candidate_withdrawal_evidence:74000000-0000-4000-8000-000000000001',
    repeat('b', 64),
    1,
    TIMESTAMPTZ '2026-08-21 09:21:00+00',
    '70000000-0000-7000-8000-000000000001',
    TIMESTAMPTZ '2026-08-21 09:21:01+00'
);
SQL
} 2>&1)"
duplicate_status=$?
set -e
if [[ ${duplicate_status} -eq 0 ]]; then
    echo "candidate application accepted more than one withdrawal" >&2
    exit 1
fi
if [[ "${duplicate_output}" != *"candidate_withdrawal_application_unique"* ]]; then
    echo "duplicate withdrawal failed for an unexpected reason: ${duplicate_output}" >&2
    exit 1
fi

set +e
rewrite_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE candidate_withdrawal_record
SET initiating_actor_reference = 'candidate:73000000-0000-4000-8000-000000000099'
WHERE candidate_withdrawal_record_id = '72000000-0000-7000-8000-000000000001';
SQL
} 2>&1)"
rewrite_status=$?
set -e
if [[ ${rewrite_status} -eq 0 || "${rewrite_output}" != *"candidate withdrawal evidence is append-only"* ]]; then
    echo "candidate withdrawal evidence was rewritable or failed unexpectedly: ${rewrite_output}" >&2
    exit 1
fi

set +e
staff_actor_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_withdrawal_record (
    tenant_record_id, candidate_withdrawal_record_id,
    candidate_application_record_id, initiating_actor_reference,
    identity_resolution_reference, identity_resolution_digest,
    withdrawal_evidence_reference, withdrawal_evidence_digest,
    evidence_version, withdrawn_at, audit_event_record_id, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000001',
    '82000000-0000-7000-8000-000000000001',
    '20000000-0000-7000-8000-000000000051',
    'staff:83000000-0000-4000-8000-000000000001',
    'identity_resolution:85000000-0000-4000-8000-000000000001',
    repeat('c', 64),
    'candidate_withdrawal_evidence:84000000-0000-4000-8000-000000000001',
    repeat('d', 64),
    1,
    TIMESTAMPTZ '2026-08-21 09:20:00+00',
    '80000000-0000-7000-8000-000000000001',
    TIMESTAMPTZ '2026-08-21 09:20:01+00'
);
SQL
} 2>&1)"
staff_actor_status=$?
set -e
if [[ ${staff_actor_status} -eq 0 || "${staff_actor_output}" != *"candidate_withdrawal_actor_reference_check"* ]]; then
    echo "staff actor could masquerade as candidate withdrawal: ${staff_actor_output}" >&2
    exit 1
fi

echo "candidate withdrawal governance contract passed"
