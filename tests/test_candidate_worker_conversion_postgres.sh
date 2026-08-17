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

TENANT_ID="10000000-0000-7000-8000-000000000001"
tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

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

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('10000000-0000-7000-8000-000000000001', 'tenant_alpha');

INSERT INTO person_record (
    tenant_record_id, person_record_id, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000001',
    TIMESTAMPTZ '2026-08-17 04:50:00+00'
);

INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000011',
    '00000000-0000-7000-8000-000000000001',
    TIMESTAMPTZ '2026-08-17 04:55:00+00'
);

INSERT INTO job_profile (
    tenant_record_id, job_profile_id, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000021',
    TIMESTAMPTZ '2026-08-17 04:40:00+00'
);

INSERT INTO candidate_profile (
    tenant_record_id, candidate_profile_id, application_status_code, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000031',
    'offer',
    TIMESTAMPTZ '2026-08-17 04:45:00+00'
);

INSERT INTO decision_evidence_set (
    tenant_record_id, decision_evidence_set_id, evidence_set_version_code,
    digest_algorithm_code, created_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000041',
    'selection_packet_v3',
    'sha256',
    TIMESTAMPTZ '2026-08-17 04:56:00+00'
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
    TIMESTAMPTZ '2026-08-17 04:57:00+00'
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
    TIMESTAMPTZ '2026-08-17 04:59:00+00',
    TIMESTAMPTZ '2026-08-17 05:00:00+00'
);
SQL

sealed_evidence_count="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM decision_evidence_set
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND decision_evidence_set_id = '00000000-0000-7000-8000-000000000041'::uuid
  AND sealed_selection_decision_id = '00000000-0000-7000-8000-000000000051'::uuid
  AND sealed_at = TIMESTAMPTZ '2026-08-17 05:00:00+00'
  AND evidence_set_digest ~ '^[0-9a-f]{64}$';
")"
if [[ "${sealed_evidence_count}" != "1" ]]; then
    echo "hire decision did not seal exactly one versioned evidence set" >&2
    exit 1
fi

set +e
legacy_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_worker_link (
    tenant_record_id, candidate_worker_link_id, candidate_profile_id,
    person_record_id, linked_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000033',
    '00000000-0000-7000-8000-000000000031',
    '00000000-0000-7000-8000-000000000001',
    TIMESTAMPTZ '2026-08-17 05:01:00+00'
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

bad_audit_event='{"data":{"high_impact":true,"result_code":"wrong_result"},"datacontenttype":"application/json","id":"00000000-0000-7000-8000-000000000061","orgmetraactor":"keyverse_subject:01JHIRINGMANAGER","orgmetraconfirmation":"confirmation:01JHUMANCONFIRM","orgmetraevidence":"decision_evidence_set:00000000-0000-7000-8000-000000000041","orgmetrapurpose":"talent_acquisition","orgmetrareason":"candidate_hire_confirmed","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:talent_core","specversion":"1.0","subject":"candidate_worker_conversion_record:00000000-0000-7000-8000-000000000081","time":"2026-08-17T05:01:00Z","type":"orgmetra.candidate.worker_converted"}'

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v canonical_event="${bad_audit_event}" <<'SQL'
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
bad_binding_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
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
    DATE '2026-08-17',
    TIMESTAMPTZ '2026-08-17 05:02:00+00'
);
SQL
} 2>&1)"
bad_binding_status=$?
set -e
if [[ ${bad_binding_status} -eq 0 ]]; then
    echo "candidate conversion accepted an audit event with the wrong governed result" >&2
    exit 1
fi
if [[ "${bad_binding_output}" != *"candidate conversion audit envelope does not bind exact hire provenance"* ]]; then
    echo "bad conversion audit binding failed for an unexpected reason: ${bad_binding_output}" >&2
    exit 1
fi

good_audit_event='{"data":{"high_impact":true,"result_code":"worker_created"},"datacontenttype":"application/json","id":"00000000-0000-7000-8000-000000000062","orgmetraactor":"keyverse_subject:01JHIRINGMANAGER","orgmetraconfirmation":"confirmation:01JHUMANCONFIRM","orgmetraevidence":"decision_evidence_set:00000000-0000-7000-8000-000000000041","orgmetrapurpose":"talent_acquisition","orgmetrareason":"candidate_hire_confirmed","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:talent_core","specversion":"1.0","subject":"candidate_worker_conversion_record:00000000-0000-7000-8000-000000000081","time":"2026-08-17T05:01:00Z","type":"orgmetra.candidate.worker_converted"}'

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v canonical_event="${good_audit_event}" <<'SQL'
SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000062'::uuid,
    '00000000-0000-7000-8000-000000000072'::uuid,
    :'canonical_event',
    encode(digest(convert_to(:'canonical_event', 'UTF8'), 'sha256'), 'hex'),
    'talent_event_sink'
);

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
    '00000000-0000-7000-8000-000000000062',
    DATE '2026-08-17',
    TIMESTAMPTZ '2026-08-17 05:02:00+00'
);
SQL

created_binding_count="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM candidate_worker_conversion_record AS conversion_record
JOIN employment_record AS employment_record
  ON employment_record.tenant_record_id = conversion_record.tenant_record_id
 AND employment_record.employment_record_id = conversion_record.employment_record_id
 AND employment_record.person_record_id = conversion_record.person_record_id
JOIN selection_decision AS selection_decision
  ON selection_decision.tenant_record_id = conversion_record.tenant_record_id
 AND selection_decision.selection_decision_id = conversion_record.selection_decision_id
WHERE conversion_record.tenant_record_id = '${TENANT_ID}'::uuid
  AND conversion_record.candidate_worker_conversion_record_id =
      '00000000-0000-7000-8000-000000000081'::uuid
  AND selection_decision.decision_code = 'hire'
  AND conversion_record.recorded_to IS NULL;
")"
if [[ "${created_binding_count}" != "1" ]]; then
    echo "governed candidate conversion did not persist exact worker, employment, and hire-decision lineage" >&2
    exit 1
fi

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE candidate_worker_conversion_record
SET recorded_to = TIMESTAMPTZ '2026-08-17 06:00:00+00'
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'
  AND candidate_worker_conversion_record_id =
      '00000000-0000-7000-8000-000000000081';
SQL

correction_audit_event='{"data":{"high_impact":true,"result_code":"worker_conversion_corrected"},"datacontenttype":"application/json","id":"00000000-0000-7000-8000-000000000063","orgmetraactor":"keyverse_subject:01JHIRINGMANAGER","orgmetraconfirmation":"confirmation:01JHUMANCONFIRM","orgmetraevidence":"decision_evidence_set:00000000-0000-7000-8000-000000000041","orgmetrapurpose":"talent_acquisition","orgmetrareason":"candidate_conversion_corrected","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:talent_core","specversion":"1.0","subject":"candidate_worker_conversion_record:00000000-0000-7000-8000-000000000082","time":"2026-08-17T06:01:00Z","type":"orgmetra.candidate.worker_conversion_corrected"}'

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v canonical_event="${correction_audit_event}" <<'SQL'
SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000063'::uuid,
    '00000000-0000-7000-8000-000000000073'::uuid,
    :'canonical_event',
    encode(digest(convert_to(:'canonical_event', 'UTF8'), 'sha256'), 'hex'),
    'talent_event_sink'
);

INSERT INTO candidate_worker_conversion_record (
    tenant_record_id, candidate_worker_conversion_record_id, candidate_profile_id,
    person_record_id, employment_record_id, selection_decision_id,
    audit_event_record_id, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000082',
    '00000000-0000-7000-8000-000000000031',
    '00000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000011',
    '00000000-0000-7000-8000-000000000051',
    '00000000-0000-7000-8000-000000000063',
    DATE '2026-08-17',
    TIMESTAMPTZ '2026-08-17 06:02:00+00'
);
SQL

history_shape="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT
    count(*) FILTER (WHERE recorded_to IS NULL)::text || ':' ||
    count(*) FILTER (WHERE recorded_to IS NOT NULL)::text
FROM candidate_worker_conversion_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND candidate_profile_id = '00000000-0000-7000-8000-000000000031'::uuid;
")"
if [[ "${history_shape}" != "1:1" ]]; then
    echo "candidate conversion correction did not preserve one closed history fact and one current fact: ${history_shape}" >&2
    exit 1
fi

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE orgmetra_candidate_conversion_reader NOLOGIN NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO orgmetra_candidate_conversion_reader;
GRANT SELECT ON candidate_worker_conversion_record TO orgmetra_candidate_conversion_reader;
SET ROLE orgmetra_candidate_conversion_reader;

DO $$
DECLARE
    visible_count bigint;
BEGIN
    PERFORM set_config('orgmetra.tenant_record_id', '', false);
    SELECT count(*) INTO visible_count FROM candidate_worker_conversion_record;
    IF visible_count <> 0 THEN
        RAISE EXCEPTION 'missing tenant context exposed candidate conversion history';
    END IF;
END;
$$;

SET orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
DO $$
DECLARE
    visible_count bigint;
BEGIN
    SELECT count(*) INTO visible_count FROM candidate_worker_conversion_record;
    IF visible_count <> 2 THEN
        RAISE EXCEPTION 'tenant alpha did not see its complete candidate conversion history';
    END IF;
END;
$$;

SET orgmetra.tenant_record_id = '20000000-0000-7000-8000-000000000001';
DO $$
DECLARE
    visible_count bigint;
BEGIN
    SELECT count(*) INTO visible_count FROM candidate_worker_conversion_record;
    IF visible_count <> 0 THEN
        RAISE EXCEPTION 'foreign tenant context exposed candidate conversion history';
    END IF;
END;
$$;

RESET ROLE;
SQL
