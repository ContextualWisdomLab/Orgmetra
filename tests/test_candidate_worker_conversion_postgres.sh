#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
TENANT_ID='10000000-0000-7000-8000-000000000001'

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0003_audit_outbox_persistence.sql \
    database/migrations/0004_outbox_delivery_claim.sql \
    database/migrations/0005_outbox_delivery_finalization.sql \
    database/migrations/0006_outbox_delivery_dead_letter.sql \
    database/migrations/0007_outbox_retry_exhaustion.sql \
    database/migrations/0008_candidate_worker_conversion_governance.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('10000000-0000-7000-8000-000000000001', 'tenant_alpha');

INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000001'
);

INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000002',
    '00000000-0000-7000-8000-000000000001'
);

INSERT INTO employment_record_version (
    tenant_record_id, employment_record_version_id, employment_record_id,
    employment_status_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000003',
    '00000000-0000-7000-8000-000000000002',
    'active', DATE '2026-03-10', TIMESTAMPTZ '2026-03-02 01:10:00+00'
);

INSERT INTO job_profile (tenant_record_id, job_profile_id)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000007'
);

INSERT INTO candidate_profile (
    tenant_record_id, candidate_profile_id, application_status_code, recorded_from
) VALUES
(
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000031',
    'offer', TIMESTAMPTZ '2026-03-01 00:00:00+00'
),
(
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000032',
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

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
INSERT INTO decision_evidence_set (
    tenant_record_id, decision_evidence_set_id, evidence_set_version_code,
    digest_algorithm_code, created_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000040',
    'hire_evidence_v1', 'sha256', TIMESTAMPTZ '2026-03-02 00:00:00+00'
);
INSERT INTO selection_decision_evidence (
    tenant_record_id, selection_decision_evidence_id, decision_evidence_set_id,
    evidence_reference, evidence_version_code, recorded_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000041',
    '00000000-0000-7000-8000-000000000040',
    'assessment:scorecard-42', 'scorecard_v3',
    TIMESTAMPTZ '2026-03-02 00:10:00+00'
);
INSERT INTO selection_decision (
    tenant_record_id, selection_decision_id, candidate_profile_id, job_profile_id,
    decision_evidence_set_id, actor_reference, purpose_code, decision_code,
    decision_reason, confirmation_reference, decided_at, recorded_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000042',
    '00000000-0000-7000-8000-000000000031',
    '00000000-0000-7000-8000-000000000007',
    '00000000-0000-7000-8000-000000000040',
    'actor:recruiter-17', 'candidate_hire', 'hire',
    'Human panel approved the versioned evidence.',
    'confirmation:panel-2026-03-02',
    TIMESTAMPTZ '2026-03-02 01:00:00+00',
    TIMESTAMPTZ '2026-03-02 01:05:00+00'
);
WITH event_payload(body) AS (
    VALUES ($event${"data":{"high_impact":true,"result_code":"worker_created"},"datacontenttype":"application/json","id":"00000000-0000-7000-8000-000000000060","orgmetraactor":"actor:recruiter-17","orgmetraconfirmation":"confirmation:panel-2026-03-02","orgmetraevidence":"decision_evidence_set:00000000-0000-7000-8000-000000000040","orgmetrapurpose":"candidate_hire","orgmetrareason":"candidate_hire_confirmed","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:hris_service","specversion":"1.0","subject":"candidate_worker_conversion_record:00000000-0000-7000-8000-000000000043","time":"2026-03-02T01:30:00Z","type":"orgmetra.candidate.worker_converted"}$event$)
)
SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000060'::uuid,
    '00000000-0000-7000-8000-000000000061'::uuid,
    body,
    encode(digest(convert_to(body, 'UTF8'), 'sha256'), 'hex'),
    'hris_audit_stream'
)
FROM event_payload;
INSERT INTO candidate_worker_conversion_record (
    tenant_record_id, candidate_worker_conversion_record_id, candidate_profile_id,
    person_record_id, employment_record_id, selection_decision_id,
    audit_event_record_id, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000043',
    '00000000-0000-7000-8000-000000000031',
    '00000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000002',
    '00000000-0000-7000-8000-000000000042',
    '00000000-0000-7000-8000-000000000060',
    DATE '2026-03-10', TIMESTAMPTZ '2026-03-02 02:00:00+00'
);
COMMIT;
SQL

visible_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM candidate_worker_conversion_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND candidate_profile_id = '00000000-0000-7000-8000-000000000031'::uuid
  AND daterange(effective_from, effective_to, '[)') @> DATE '2026-03-10'
  AND tstzrange(recorded_from, recorded_to, '[)') @> TIMESTAMPTZ '2026-03-03 00:00:00+00';
")"
if [[ "${visible_count}" != "1" ]]; then
    echo "expected one governed conversion at the business/knowledge coordinate, got ${visible_count}" >&2
    exit 1
fi

audit_binding_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM candidate_worker_conversion_record AS conversion
JOIN audit_event_record AS audit
  ON audit.tenant_record_id = conversion.tenant_record_id
 AND audit.audit_event_record_id = conversion.audit_event_record_id
JOIN outbox_delivery_record AS delivery
  ON delivery.tenant_record_id = audit.tenant_record_id
 AND delivery.audit_event_record_id = audit.audit_event_record_id
WHERE conversion.tenant_record_id = '${TENANT_ID}'::uuid
  AND conversion.candidate_worker_conversion_record_id = '00000000-0000-7000-8000-000000000043'::uuid;
")"
if [[ "${audit_binding_count}" != "1" ]]; then
    echo "expected exact immutable audit/outbox binding for governed conversion, got ${audit_binding_count}" >&2
    exit 1
fi

set +e
mismatched_candidate_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_worker_conversion_record (
    tenant_record_id, candidate_worker_conversion_record_id, candidate_profile_id,
    person_record_id, employment_record_id, selection_decision_id,
    audit_event_record_id, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000054',
    '00000000-0000-7000-8000-000000000032',
    '00000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000002',
    '00000000-0000-7000-8000-000000000042',
    '00000000-0000-7000-8000-000000000060',
    DATE '2026-03-10', TIMESTAMPTZ '2026-03-02 02:10:00+00'
);
SQL
} 2>&1)"
mismatched_candidate_status=$?
set -e
if [[ ${mismatched_candidate_status} -eq 0 ]]; then
    echo "candidate conversion accepted a hire decision for another candidate" >&2
    exit 1
fi
if [[ "${mismatched_candidate_output}" != *"candidate conversion decision belongs to a different candidate"* ]]; then
    echo "candidate mismatch failed for an unexpected reason: ${mismatched_candidate_output}" >&2
    exit 1
fi

set +e
knowledge_overlap_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
WITH event_payload(body) AS (
    VALUES ($event${"data":{"high_impact":true,"result_code":"worker_created"},"datacontenttype":"application/json","id":"00000000-0000-7000-8000-000000000062","orgmetraactor":"actor:recruiter-17","orgmetraconfirmation":"confirmation:panel-2026-03-02","orgmetraevidence":"decision_evidence_set:00000000-0000-7000-8000-000000000040","orgmetrapurpose":"candidate_hire","orgmetrareason":"candidate_hire_confirmed","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:hris_service","specversion":"1.0","subject":"candidate_worker_conversion_record:00000000-0000-7000-8000-000000000044","time":"2026-03-02T02:20:00Z","type":"orgmetra.candidate.worker_converted"}$event$)
)
SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000062'::uuid,
    '00000000-0000-7000-8000-000000000063'::uuid,
    body,
    encode(digest(convert_to(body, 'UTF8'), 'sha256'), 'hex'),
    'hris_audit_stream'
)
FROM event_payload;
INSERT INTO candidate_worker_conversion_record (
    tenant_record_id, candidate_worker_conversion_record_id, candidate_profile_id,
    person_record_id, employment_record_id, selection_decision_id,
    audit_event_record_id, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000044',
    '00000000-0000-7000-8000-000000000031',
    '00000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000002',
    '00000000-0000-7000-8000-000000000042',
    '00000000-0000-7000-8000-000000000062',
    DATE '2027-01-01', TIMESTAMPTZ '2026-03-02 03:00:00+00'
);
COMMIT;
SQL
} 2>&1)"
knowledge_overlap_status=$?
set -e
if [[ ${knowledge_overlap_status} -eq 0 ]]; then
    echo "one candidate unexpectedly produced two simultaneously current conversion facts" >&2
    exit 1
fi
if [[ "${knowledge_overlap_output}" != *"candidate_conversion_knowledge_exclusion"* ]]; then
    echo "candidate current-knowledge conflict failed for an unexpected reason: ${knowledge_overlap_output}" >&2
    exit 1
fi

rolled_back_audit_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*) FROM audit_event_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND audit_event_record_id = '00000000-0000-7000-8000-000000000062'::uuid;
")"
if [[ "${rolled_back_audit_count}" != "0" ]]; then
    echo "failed conversion left orphan audit/outbox evidence instead of rolling back atomically" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO decision_evidence_set (
    tenant_record_id, decision_evidence_set_id, evidence_set_version_code,
    digest_algorithm_code, created_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000050',
    'reject_evidence_v1', 'sha256', TIMESTAMPTZ '2026-03-03 00:00:00+00'
);
INSERT INTO selection_decision_evidence (
    tenant_record_id, selection_decision_evidence_id, decision_evidence_set_id,
    evidence_reference, evidence_version_code, recorded_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000051',
    '00000000-0000-7000-8000-000000000050',
    'assessment:scorecard-43', 'scorecard_v3',
    TIMESTAMPTZ '2026-03-03 00:10:00+00'
);
INSERT INTO selection_decision (
    tenant_record_id, selection_decision_id, candidate_profile_id, job_profile_id,
    decision_evidence_set_id, actor_reference, purpose_code, decision_code,
    decision_reason, confirmation_reference, decided_at, recorded_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000052',
    '00000000-0000-7000-8000-000000000031',
    '00000000-0000-7000-8000-000000000007',
    '00000000-0000-7000-8000-000000000050',
    'actor:recruiter-18', 'candidate_hire', 'reject',
    'Human panel did not approve the evidence.',
    'confirmation:panel-2026-03-03',
    TIMESTAMPTZ '2026-03-03 01:00:00+00',
    TIMESTAMPTZ '2026-03-03 01:05:00+00'
);
SQL

set +e
non_hire_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_worker_conversion_record (
    tenant_record_id, candidate_worker_conversion_record_id, candidate_profile_id,
    person_record_id, employment_record_id, selection_decision_id,
    audit_event_record_id, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000053',
    '00000000-0000-7000-8000-000000000031',
    '00000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000002',
    '00000000-0000-7000-8000-000000000052',
    '00000000-0000-7000-8000-000000000060',
    DATE '2026-03-10', TIMESTAMPTZ '2026-03-03 02:00:00+00'
);
SQL
} 2>&1)"
non_hire_status=$?
set -e
if [[ ${non_hire_status} -eq 0 ]]; then
    echo "non-hire selection decision unexpectedly created worker lineage" >&2
    exit 1
fi
if [[ "${non_hire_output}" != *"candidate conversion requires a hire selection decision"* ]]; then
    echo "non-hire conversion failed for an unexpected reason: ${non_hire_output}" >&2
    exit 1
fi

set +e
mutation_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
UPDATE candidate_worker_conversion_record
SET effective_from = DATE '2026-03-11'
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND candidate_worker_conversion_record_id = '00000000-0000-7000-8000-000000000043'::uuid;
"; } 2>&1)"
mutation_status=$?
set -e
if [[ ${mutation_status} -eq 0 ]]; then
    echo "in-place candidate conversion business mutation unexpectedly succeeded" >&2
    exit 1
fi
if [[ "${mutation_output}" != *"bitemporal correction may only close an open recorded interval"* ]]; then
    echo "candidate conversion mutation failed for an unexpected reason: ${mutation_output}" >&2
    exit 1
fi

rls_state="$(psql "${DATABASE_URL}" -Atqc "
SELECT relrowsecurity::int || ':' || relforcerowsecurity::int
FROM pg_class
WHERE oid = 'candidate_worker_conversion_record'::regclass;
")"
if [[ "${rls_state}" != "1:1" ]]; then
    echo "candidate conversion relation must enable and force tenant RLS, got ${rls_state}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
UPDATE candidate_worker_conversion_record
SET recorded_to = TIMESTAMPTZ '2026-04-01 00:00:00+00'
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'
  AND candidate_worker_conversion_record_id = '00000000-0000-7000-8000-000000000043';
WITH event_payload(body) AS (
    VALUES ($event${"data":{"high_impact":true,"result_code":"worker_conversion_corrected"},"datacontenttype":"application/json","id":"00000000-0000-7000-8000-000000000064","orgmetraactor":"actor:recruiter-17","orgmetraconfirmation":"confirmation:panel-2026-03-02","orgmetraevidence":"decision_evidence_set:00000000-0000-7000-8000-000000000040","orgmetrapurpose":"candidate_hire","orgmetrareason":"candidate_conversion_corrected","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:hris_service","specversion":"1.0","subject":"candidate_worker_conversion_record:00000000-0000-7000-8000-000000000045","time":"2026-04-01T00:10:00Z","type":"orgmetra.candidate.worker_conversion_corrected"}$event$)
)
SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000064'::uuid,
    '00000000-0000-7000-8000-000000000065'::uuid,
    body,
    encode(digest(convert_to(body, 'UTF8'), 'sha256'), 'hex'),
    'hris_audit_stream'
)
FROM event_payload;
INSERT INTO candidate_worker_conversion_record (
    tenant_record_id, candidate_worker_conversion_record_id, candidate_profile_id,
    person_record_id, employment_record_id, selection_decision_id,
    audit_event_record_id, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000045',
    '00000000-0000-7000-8000-000000000031',
    '00000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000002',
    '00000000-0000-7000-8000-000000000042',
    '00000000-0000-7000-8000-000000000064',
    DATE '2026-03-11', TIMESTAMPTZ '2026-04-01 00:20:00+00'
);
COMMIT;
SQL

old_knowledge_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM candidate_worker_conversion_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND candidate_profile_id = '00000000-0000-7000-8000-000000000031'::uuid
  AND effective_from = DATE '2026-03-10'
  AND tstzrange(recorded_from, recorded_to, '[)') @> TIMESTAMPTZ '2026-03-15 00:00:00+00';
")"
new_knowledge_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM candidate_worker_conversion_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND candidate_profile_id = '00000000-0000-7000-8000-000000000031'::uuid
  AND effective_from = DATE '2026-03-11'
  AND tstzrange(recorded_from, recorded_to, '[)') @> TIMESTAMPTZ '2026-04-02 00:00:00+00';
")"
current_knowledge_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM candidate_worker_conversion_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND candidate_profile_id = '00000000-0000-7000-8000-000000000031'::uuid
  AND tstzrange(recorded_from, recorded_to, '[)') @> TIMESTAMPTZ '2026-04-02 00:00:00+00';
")"
if [[ "${old_knowledge_count}" != "1" || "${new_knowledge_count}" != "1" || "${current_knowledge_count}" != "1" ]]; then
    echo "candidate conversion correction did not preserve one historical/current knowledge fact: old=${old_knowledge_count} new=${new_knowledge_count} current=${current_knowledge_count}" >&2
    exit 1
fi

correction_audit_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM candidate_worker_conversion_record AS conversion
JOIN audit_event_record AS audit
  ON audit.tenant_record_id = conversion.tenant_record_id
 AND audit.audit_event_record_id = conversion.audit_event_record_id
WHERE conversion.tenant_record_id = '${TENANT_ID}'::uuid
  AND conversion.candidate_worker_conversion_record_id = '00000000-0000-7000-8000-000000000045'::uuid
  AND audit.canonical_event_json::jsonb ->> 'type' = 'orgmetra.candidate.worker_conversion_corrected'
  AND audit.canonical_event_json::jsonb ->> 'orgmetrareason' = 'candidate_conversion_corrected'
  AND audit.canonical_event_json::jsonb #>> '{data,result_code}' = 'worker_conversion_corrected';
")"
if [[ "${correction_audit_count}" != "1" ]]; then
    echo "candidate conversion correction lacks correction-specific immutable audit evidence" >&2
    exit 1
fi

echo "PostgreSQL governed candidate-to-worker conversion contract passed"
