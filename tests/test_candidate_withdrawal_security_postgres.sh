#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

# This security contract intentionally runs after test_candidate_withdrawal_postgres.sh
# in the same PostgreSQL service. The predecessor script owns schema/fixture setup;
# this script isolates adversarial cases so each rejection has one causal boundary.
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

# A second otherwise-valid audit event must not allow a second withdrawal for the
# same application. Using a distinct audit ID isolates the application uniqueness
# invariant from audit-event uniqueness.
record_event \
    '70000000-0000-7000-8000-000000000002' \
    '71000000-0000-7000-8000-000000000002' \
    '10000000-0000-7000-8000-000000000001' \
    'candidate_withdrawal_record:72000000-0000-7000-8000-000000000002' \
    'candidate:73000000-0000-4000-8000-000000000001' \
    'candidate_withdrawal_evidence:74000000-0000-4000-8000-000000000002' \
    '2026-08-21T09:21:00Z'

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
    'identity_resolution:75000000-0000-4000-8000-000000000002',
    repeat('c', 64),
    'candidate_withdrawal_evidence:74000000-0000-4000-8000-000000000002',
    repeat('d', 64),
    2,
    TIMESTAMPTZ '2026-08-21 09:21:00+00',
    '70000000-0000-7000-8000-000000000002',
    TIMESTAMPTZ '2026-08-21 09:21:01+00'
);
SQL
} 2>&1)"
duplicate_status=$?
set -e
if [[ ${duplicate_status} -eq 0 || "${duplicate_output}" != *"candidate_withdrawal_application_unique"* ]]; then
    echo "duplicate withdrawal did not fail at the application uniqueness boundary: ${duplicate_output}" >&2
    exit 1
fi

# A fully valid generic audit envelope with a staff actor must still be rejected by
# the withdrawal relation itself. This prevents the generic audit API from being
# used to relabel a staff-driven adverse action as candidate withdrawal.
record_event \
    '80000000-0000-7000-8000-000000000001' \
    '81000000-0000-7000-8000-000000000001' \
    '20000000-0000-7000-8000-000000000001' \
    'candidate_withdrawal_record:82000000-0000-7000-8000-000000000001' \
    'staff:83000000-0000-4000-8000-000000000001' \
    'candidate_withdrawal_evidence:84000000-0000-4000-8000-000000000001' \
    '2026-08-21T09:20:00Z'

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
    repeat('e', 64),
    'candidate_withdrawal_evidence:84000000-0000-4000-8000-000000000001',
    repeat('f', 64),
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

# Candidate-shaped actor text is not enough: the immutable audit envelope must bind
# the exact evidence reference supplied by the withdrawal row.
record_event \
    '80000000-0000-7000-8000-000000000002' \
    '81000000-0000-7000-8000-000000000002' \
    '20000000-0000-7000-8000-000000000001' \
    'candidate_withdrawal_record:82000000-0000-7000-8000-000000000002' \
    'candidate:83000000-0000-4000-8000-000000000002' \
    'candidate_withdrawal_evidence:84000000-0000-4000-8000-000000000002' \
    '2026-08-21T09:22:00Z'

set +e
forged_evidence_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_withdrawal_record (
    tenant_record_id, candidate_withdrawal_record_id,
    candidate_application_record_id, initiating_actor_reference,
    identity_resolution_reference, identity_resolution_digest,
    withdrawal_evidence_reference, withdrawal_evidence_digest,
    evidence_version, withdrawn_at, audit_event_record_id, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000001',
    '82000000-0000-7000-8000-000000000002',
    '20000000-0000-7000-8000-000000000051',
    'candidate:83000000-0000-4000-8000-000000000002',
    'identity_resolution:85000000-0000-4000-8000-000000000002',
    repeat('1', 64),
    'candidate_withdrawal_evidence:84000000-0000-4000-8000-000000000099',
    repeat('2', 64),
    1,
    TIMESTAMPTZ '2026-08-21 09:22:00+00',
    '80000000-0000-7000-8000-000000000002',
    TIMESTAMPTZ '2026-08-21 09:22:01+00'
);
SQL
} 2>&1)"
forged_evidence_status=$?
set -e
if [[ ${forged_evidence_status} -eq 0 || "${forged_evidence_output}" != *"candidate withdrawal audit envelope does not bind exact candidate provenance"* ]]; then
    echo "withdrawal accepted audit/evidence mismatch: ${forged_evidence_output}" >&2
    exit 1
fi

# Persist one valid Beta withdrawal so RLS can prove positive visibility in both
# tenants rather than only proving absence.
record_event \
    '80000000-0000-7000-8000-000000000003' \
    '81000000-0000-7000-8000-000000000003' \
    '20000000-0000-7000-8000-000000000001' \
    'candidate_withdrawal_record:82000000-0000-7000-8000-000000000003' \
    'candidate:83000000-0000-4000-8000-000000000003' \
    'candidate_withdrawal_evidence:84000000-0000-4000-8000-000000000003' \
    '2026-08-21T09:23:00Z'

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_withdrawal_record (
    tenant_record_id, candidate_withdrawal_record_id,
    candidate_application_record_id, initiating_actor_reference,
    identity_resolution_reference, identity_resolution_digest,
    withdrawal_evidence_reference, withdrawal_evidence_digest,
    evidence_version, withdrawn_at, audit_event_record_id, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000001',
    '82000000-0000-7000-8000-000000000003',
    '20000000-0000-7000-8000-000000000051',
    'candidate:83000000-0000-4000-8000-000000000003',
    'identity_resolution:85000000-0000-4000-8000-000000000003',
    repeat('3', 64),
    'candidate_withdrawal_evidence:84000000-0000-4000-8000-000000000003',
    repeat('4', 64),
    1,
    TIMESTAMPTZ '2026-08-21 09:23:00+00',
    '80000000-0000-7000-8000-000000000003',
    TIMESTAMPTZ '2026-08-21 09:23:01+00'
);

CREATE ROLE orgmetra_candidate_withdrawal_reader NOLOGIN NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO orgmetra_candidate_withdrawal_reader;
GRANT SELECT ON candidate_withdrawal_record TO orgmetra_candidate_withdrawal_reader;

SET ROLE orgmetra_candidate_withdrawal_reader;

DO $$
DECLARE
    visible_count bigint;
BEGIN
    SELECT count(*) INTO visible_count FROM candidate_withdrawal_record;
    IF visible_count <> 0 THEN
        RAISE EXCEPTION 'missing tenant context exposed candidate withdrawal evidence: %', visible_count;
    END IF;
END;
$$;

SET orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
DO $$
DECLARE
    visible_count bigint;
    wrong_tenant_count bigint;
BEGIN
    SELECT count(*) INTO visible_count FROM candidate_withdrawal_record;
    SELECT count(*) INTO wrong_tenant_count
    FROM candidate_withdrawal_record
    WHERE tenant_record_id <> '10000000-0000-7000-8000-000000000001'::uuid;
    IF visible_count <> 1 OR wrong_tenant_count <> 0 THEN
        RAISE EXCEPTION 'tenant Alpha withdrawal visibility was not isolated: visible=%, wrong=%',
            visible_count, wrong_tenant_count;
    END IF;
END;
$$;

SET orgmetra.tenant_record_id = '20000000-0000-7000-8000-000000000001';
DO $$
DECLARE
    visible_count bigint;
    wrong_tenant_count bigint;
BEGIN
    SELECT count(*) INTO visible_count FROM candidate_withdrawal_record;
    SELECT count(*) INTO wrong_tenant_count
    FROM candidate_withdrawal_record
    WHERE tenant_record_id <> '20000000-0000-7000-8000-000000000001'::uuid;
    IF visible_count <> 1 OR wrong_tenant_count <> 0 THEN
        RAISE EXCEPTION 'tenant Beta withdrawal visibility was not isolated: visible=%, wrong=%',
            visible_count, wrong_tenant_count;
    END IF;
END;
$$;

RESET ROLE;
SQL

set +e
truncate_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c 'TRUNCATE candidate_withdrawal_record;' ; } 2>&1)"
truncate_status=$?
set -e
if [[ ${truncate_status} -eq 0 || "${truncate_output}" != *"candidate withdrawal evidence cannot be truncated"* ]]; then
    echo "candidate withdrawal evidence could be truncated or failed unexpectedly: ${truncate_output}" >&2
    exit 1
fi

echo "candidate withdrawal anti-forgery and tenant-isolation contract passed"
