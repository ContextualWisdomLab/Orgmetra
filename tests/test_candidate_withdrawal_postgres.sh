#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

# This is the executable persistence contract for candidate-initiated withdrawal.
# It applies the complete stack, proves a governed withdrawal can be recorded,
# proves the raw application-stage shortcut remains closed, and proves the
# resulting governance evidence cannot be rewritten.
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

INSERT INTO candidate_application_record (
    tenant_record_id, candidate_application_record_id, candidate_profile_id,
    requisition_reference, submitted_at, recorded_from
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
    local identity_reference="$8"
    local identity_digest="$9"
    local withdrawal_digest="${10}"
    local evidence_version="${11}"

    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
        --set=event_id="${event_id}" \
        --set=outbox_id="${outbox_id}" \
        --set=tenant_id="${tenant_id}" \
        --set=subject="${subject}" \
        --set=actor="${actor}" \
        --set=evidence="${evidence}" \
        --set=event_time="${event_time}" \
        --set=identity_reference="${identity_reference}" \
        --set=identity_digest="${identity_digest}" \
        --set=withdrawal_digest="${withdrawal_digest}" \
        --set=evidence_version="${evidence_version}" <<'SQL'
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
            'result_code', 'application_withdrawn',
            'evidence_version', :'evidence_version'::integer,
            'identity_resolution_reference', :'identity_reference',
            'identity_resolution_digest', :'identity_digest',
            'withdrawal_evidence_digest', :'withdrawal_digest'
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
    '2026-08-21T09:20:00Z' \
    'identity_resolution:75000000-0000-4000-8000-000000000001' \
    "$(printf 'a%.0s' {1..64})" \
    "$(printf 'b%.0s' {1..64})" \
    '1'

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

persisted_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
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
raw_stage_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_application_stage_record (
    tenant_record_id,
    candidate_application_stage_record_id,
    candidate_application_record_id,
    application_stage_code,
    effective_from,
    recorded_from
) VALUES (
    '20000000-0000-7000-8000-000000000001',
    '20000000-0000-7000-8000-000000000061',
    '20000000-0000-7000-8000-000000000051',
    'withdrawn',
    TIMESTAMPTZ '2026-08-21 09:20:00+00',
    TIMESTAMPTZ '2026-08-21 09:20:01+00'
);
SQL
} 2>&1)"
raw_stage_status=$?
set -e
if [[ ${raw_stage_status} -eq 0 ]]; then
    echo "raw application stage reintroduced unproven withdrawn state" >&2
    exit 1
fi
if [[ "${raw_stage_output}" != *"candidate_application_stage_code_check"* ]]; then
    echo "raw withdrawn stage failed for an unexpected reason: ${raw_stage_output}" >&2
    exit 1
fi

set +e
rewrite_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE candidate_withdrawal_record
SET initiating_actor_reference = 'candidate:73000000-0000-4000-8000-000000000099'
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'
  AND candidate_withdrawal_record_id = '72000000-0000-7000-8000-000000000001';
SQL
} 2>&1)"
rewrite_status=$?
set -e
if [[ ${rewrite_status} -eq 0 ]]; then
    echo "candidate withdrawal evidence was rewritten in place" >&2
    exit 1
fi
if [[ "${rewrite_output}" != *"candidate withdrawal evidence is append-only"* ]]; then
    echo "withdrawal rewrite failed for an unexpected reason: ${rewrite_output}" >&2
    exit 1
fi

echo "candidate withdrawal persistence contract passed"
