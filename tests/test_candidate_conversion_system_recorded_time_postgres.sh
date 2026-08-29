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
    database/migrations/0009_candidate_worker_conversion_governance.sql \
    database/migrations/0017_candidate_conversion_system_recorded_time.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="10000000-0000-7000-8000-000000000001"
tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('10000000-0000-7000-8000-000000000001', 'tenant_alpha');

INSERT INTO person_record (tenant_record_id, person_record_id, recorded_from)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000001',
    pg_catalog.transaction_timestamp()
);

INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000011',
    '00000000-0000-7000-8000-000000000001',
    pg_catalog.transaction_timestamp()
);

INSERT INTO job_profile (tenant_record_id, job_profile_id, recorded_from)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000021',
    pg_catalog.transaction_timestamp()
);

INSERT INTO candidate_profile (
    tenant_record_id, candidate_profile_id, application_status_code, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000031',
    'offer',
    pg_catalog.transaction_timestamp()
);

INSERT INTO decision_evidence_set (
    tenant_record_id, decision_evidence_set_id, evidence_set_version_code,
    digest_algorithm_code, created_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000041',
    'selection_packet_v3',
    'sha256',
    pg_catalog.transaction_timestamp() - INTERVAL '10 minutes'
);

INSERT INTO selection_decision_evidence (
    tenant_record_id, selection_decision_evidence_id, decision_evidence_set_id,
    evidence_reference, evidence_version_code, recorded_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000042',
    '00000000-0000-7000-8000-000000000041',
    'structured_interview:panel_17',
    'rubric_v5',
    pg_catalog.transaction_timestamp() - INTERVAL '9 minutes'
);

INSERT INTO selection_decision (
    tenant_record_id, selection_decision_id, candidate_profile_id, job_profile_id,
    decision_evidence_set_id, actor_reference, purpose_code, decision_code,
    decision_reason, confirmation_reference, decided_at, recorded_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000051',
    '00000000-0000-7000-8000-000000000031',
    '00000000-0000-7000-8000-000000000021',
    '00000000-0000-7000-8000-000000000041',
    'keyverse_subject:01JHIRINGMANAGER',
    'talent_acquisition',
    'hire',
    'Structured interview and verified role evidence supported hire',
    'confirmation:01JHUMANCONFIRM',
    pg_catalog.transaction_timestamp() - INTERVAL '8 minutes',
    pg_catalog.transaction_timestamp() - INTERVAL '7 minutes'
);
SQL

build_event() {
    local event_id="$1"
    local subject_id="$2"
    local event_type="${3:-orgmetra.candidate.worker_converted}"
    local reason_code="${4:-candidate_hire_confirmed}"
    local result_code="${5:-worker_created}"
    tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT pg_catalog.jsonb_build_object(
    'data', pg_catalog.jsonb_build_object('high_impact', true, 'result_code', '${result_code}'),
    'datacontenttype', 'application/json',
    'id', '${event_id}',
    'orgmetraactor', 'keyverse_subject:01JHIRINGMANAGER',
    'orgmetraconfirmation', 'confirmation:01JHUMANCONFIRM',
    'orgmetraevidence', 'decision_evidence_set:00000000-0000-7000-8000-000000000041',
    'orgmetrapurpose', 'talent_acquisition',
    'orgmetrareason', '${reason_code}',
    'orgmetratenant', '${TENANT_ID}',
    'source', 'urn:orgmetra:talent_core',
    'specversion', '1.0',
    'subject', 'candidate_worker_conversion_record:${subject_id}',
    'time', pg_catalog.to_char(
        (pg_catalog.transaction_timestamp() AT TIME ZONE 'UTC') - INTERVAL '3 minutes',
        'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'
    ),
    'type', '${event_type}'
)::text;
"
}

backdated_event="$(build_event \
    '00000000-0000-7000-8000-000000000061' \
    '00000000-0000-7000-8000-000000000081')"

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v canonical_event="${backdated_event}" <<'SQL'
SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000061'::uuid,
    '00000000-0000-7000-8000-000000000071'::uuid,
    :'canonical_event',
    encode(digest(convert_to(:'canonical_event', 'UTF8'), 'sha256'), 'hex'),
    'talent_event_sink'
);
SQL

set +e
backdated_output="$({ tenant_psql "${DATABASE_URL}" --set=VERBOSITY=verbose -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_worker_conversion_record (
    tenant_record_id, candidate_worker_conversion_record_id, candidate_profile_id,
    person_record_id, employment_record_id, selection_decision_id,
    audit_event_record_id, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000081',
    '00000000-0000-7000-8000-000000000031',
    '00000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000011',
    '00000000-0000-7000-8000-000000000051',
    '00000000-0000-7000-8000-000000000061',
    CURRENT_DATE,
    pg_catalog.transaction_timestamp() - INTERVAL '2 minutes'
);
SQL
} 2>&1)"
backdated_status=$?
set -e

if [[ ${backdated_status} -eq 0 ]]; then
    echo "candidate conversion accepted caller-authored historical recorded_from" >&2
    exit 1
fi
if [[ "${backdated_output}" != *"ERROR:  23514: candidate worker conversion recorded_from must equal system transaction time"* ]]; then
    echo "backdated candidate conversion failed for an unexpected reason: ${backdated_output}" >&2
    exit 1
fi

good_event="$(build_event \
    '00000000-0000-7000-8000-000000000062' \
    '00000000-0000-7000-8000-000000000082')"

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v canonical_event="${good_event}" <<'SQL'
SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000062'::uuid,
    '00000000-0000-7000-8000-000000000072'::uuid,
    :'canonical_event',
    encode(digest(convert_to(:'canonical_event', 'UTF8'), 'sha256'), 'hex'),
    'talent_event_sink'
);
SQL

system_time_match="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
INSERT INTO candidate_worker_conversion_record (
    tenant_record_id, candidate_worker_conversion_record_id, candidate_profile_id,
    person_record_id, employment_record_id, selection_decision_id,
    audit_event_record_id, effective_from
) VALUES (
    '${TENANT_ID}',
    '00000000-0000-7000-8000-000000000082',
    '00000000-0000-7000-8000-000000000031',
    '00000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000011',
    '00000000-0000-7000-8000-000000000051',
    '00000000-0000-7000-8000-000000000062',
    CURRENT_DATE
)
RETURNING recorded_from = pg_catalog.transaction_timestamp();
")"
if [[ "${system_time_match}" != "t" ]]; then
    echo "server-authored candidate conversion did not persist transaction system time" >&2
    exit 1
fi

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE candidate_worker_conversion_record
SET recorded_to = pg_catalog.transaction_timestamp()
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'::uuid
  AND candidate_worker_conversion_record_id = '00000000-0000-7000-8000-000000000082'::uuid;
SQL

correction_event="$(build_event \
    '00000000-0000-7000-8000-000000000063' \
    '00000000-0000-7000-8000-000000000083' \
    'orgmetra.candidate.worker_conversion_corrected' \
    'candidate_conversion_corrected' \
    'worker_conversion_corrected')"

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v canonical_event="${correction_event}" <<'SQL'
SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000063'::uuid,
    '00000000-0000-7000-8000-000000000073'::uuid,
    :'canonical_event',
    encode(digest(convert_to(:'canonical_event', 'UTF8'), 'sha256'), 'hex'),
    'talent_event_sink'
);
SQL

correction_system_time_match="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
INSERT INTO candidate_worker_conversion_record (
    tenant_record_id, candidate_worker_conversion_record_id, candidate_profile_id,
    person_record_id, employment_record_id, selection_decision_id,
    audit_event_record_id, effective_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000083',
    '00000000-0000-7000-8000-000000000031',
    '00000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000011',
    '00000000-0000-7000-8000-000000000051',
    '00000000-0000-7000-8000-000000000063',
    CURRENT_DATE
)
RETURNING recorded_from = pg_catalog.transaction_timestamp();
")"
if [[ "${correction_system_time_match}" != "t" ]]; then
    echo "candidate conversion correction did not persist transaction system time" >&2
    exit 1
fi

echo "candidate conversion system-recorded-time contract passed"
