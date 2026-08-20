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
    database/migrations/0010_validity_study_case_integrity.sql \
    database/migrations/0011_criterion_observation_scope.sql \
    database/migrations/0012_people_mutation_idempotency.sql \
    database/migrations/0013_job_analysis_snapshot.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="10000000-0000-7000-8000-000000000001"
OTHER_TENANT_ID="20000000-0000-7000-8000-000000000002"
JOB_ID="00000000-0000-7000-8000-000000000021"
ANALYSIS_ID="00000000-0000-7000-8000-000000000081"
TASK_ID="00000000-0000-7000-8000-000000000082"
KSAO_ID="00000000-0000-7000-8000-000000000083"
POSITION_ID="00000000-0000-7000-8000-000000000084"
ORG_ID="00000000-0000-7000-8000-000000000085"
CRITERION_ID="00000000-0000-7000-8000-000000000086"
COMMAND_ID="00000000-0000-7000-8000-000000000087"
AUDIT_ID="00000000-0000-4000-8000-000000000088"
OUTBOX_ID="00000000-0000-4000-8000-000000000089"


tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}', 'tenant_alpha');

INSERT INTO job_profile (tenant_record_id, job_profile_id, recorded_from)
VALUES ('${TENANT_ID}', '${JOB_ID}', TIMESTAMPTZ '2026-08-17 04:40:00+00');
SQL

set +e
missing_job_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO job_analysis_snapshot (
    tenant_record_id, analysis_record_id, job_profile_id, analysis_version_code,
    status_code, effective_from, recorded_at, content_digest_sha256,
    data_function_code, people_function_code, things_function_code,
    fja_source_uri, fja_source_title, fja_source_version_code, fja_retrieved_at,
    fja_content_digest_sha256, fja_origin_code
) VALUES (
    '${TENANT_ID}', '${ANALYSIS_ID}', '00000000-0000-7000-8000-000000000099',
    'clinical-psychologist:v1', 'analysis_validated', DATE '2026-08-01',
    TIMESTAMPTZ '2026-08-18 05:00:00+00',
    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    1, 0, 7,
    'https://www.dol.gov/agencies/oalj/PUBLIC/DOT/REFERENCES/DOTAPPB',
    'Dictionary of Occupational Titles Appendix B', 'dot:1991',
    TIMESTAMPTZ '2026-08-18 03:00:00+00',
    'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
    'authoritative_occupation_source'
);
" ; } 2>&1)"
missing_job_status=$?
set -e
if [[ ${missing_job_status} -eq 0 ]]; then
    echo "job-analysis snapshot accepted a missing job_profile" >&2
    exit 1
fi
if [[ "${missing_job_output}" != *"foreign key"* && "${missing_job_output}" != *"job_analysis_snapshot_job_tenant_fk"* ]]; then
    echo "missing job failed for an unexpected reason: ${missing_job_output}" >&2
    exit 1
fi

set +e
missing_position_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO job_analysis_snapshot (
    tenant_record_id, analysis_record_id, job_profile_id, position_record_id,
    analysis_version_code, status_code, effective_from, recorded_at,
    content_digest_sha256, data_function_code, people_function_code,
    things_function_code, fja_source_uri, fja_source_title,
    fja_source_version_code, fja_retrieved_at, fja_content_digest_sha256,
    fja_origin_code
) VALUES (
    '${TENANT_ID}', '${ANALYSIS_ID}', '${JOB_ID}', '${POSITION_ID}',
    'clinical-psychologist:v1', 'analysis_validated', DATE '2026-08-01',
    TIMESTAMPTZ '2026-08-18 05:00:00+00',
    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    1, 0, 7,
    'https://www.dol.gov/agencies/oalj/PUBLIC/DOT/REFERENCES/DOTAPPB',
    'Dictionary of Occupational Titles Appendix B', 'dot:1991',
    TIMESTAMPTZ '2026-08-18 03:00:00+00',
    'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
    'authoritative_occupation_source'
);
" ; } 2>&1)"
missing_position_status=$?
set -e
if [[ ${missing_position_status} -eq 0 ]]; then
    echo "job-analysis snapshot accepted a missing position_record" >&2
    exit 1
fi
if [[ "${missing_position_output}" != *"foreign key"* \
    && "${missing_position_output}" != *"job_analysis_snapshot_position_tenant_fk"* ]]; then
    echo "missing position failed for an unexpected reason: ${missing_position_output}" >&2
    exit 1
fi

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO organization_unit (tenant_record_id, organization_unit_id, recorded_from)
VALUES ('${TENANT_ID}', '${ORG_ID}', TIMESTAMPTZ '2026-08-17 04:30:00+00');

INSERT INTO position_record (
    tenant_record_id, position_record_id, organization_unit_id, job_profile_id, recorded_from
) VALUES (
    '${TENANT_ID}', '${POSITION_ID}', '${ORG_ID}', '${JOB_ID}', TIMESTAMPTZ '2026-08-17 04:35:00+00'
);

INSERT INTO criterion_blueprint (
    tenant_record_id, criterion_blueprint_id, job_profile_id, criterion_type_code,
    criterion_version_code, effective_from, recorded_from
) VALUES (
    '${TENANT_ID}', '${CRITERION_ID}', '${JOB_ID}', 'clinical_outcome',
    'criterion:v1', DATE '2026-08-01', TIMESTAMPTZ '2026-08-17 04:36:00+00'
);
SQL

canonical_event='{"data":{"high_impact":false,"result_code":"recorded"},"datacontenttype":"application/json","id":"00000000-0000-4000-8000-000000000088","orgmetraactor":"keyverse_subject:01JACTOROPAQUE","orgmetraevidence":"clinical-psychologist:v1","orgmetrapurpose":"job_analysis_write","orgmetrareason":"snapshot_persisted","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:job_analysis_api","specversion":"1.0","subject":"job_analysis_snapshot:00000000000070008000000000000081","time":"2026-08-18T05:00:00Z","type":"orgmetra.job_architecture.snapshot_recorded"}'
canonical_digest="$(python3 - <<'PY'
from hashlib import sha256
event = '{"data":{"high_impact":false,"result_code":"recorded"},"datacontenttype":"application/json","id":"00000000-0000-4000-8000-000000000088","orgmetraactor":"keyverse_subject:01JACTOROPAQUE","orgmetraevidence":"clinical-psychologist:v1","orgmetrapurpose":"job_analysis_write","orgmetrareason":"snapshot_persisted","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:job_analysis_api","specversion":"1.0","subject":"job_analysis_snapshot:00000000000070008000000000000081","time":"2026-08-18T05:00:00Z","type":"orgmetra.job_architecture.snapshot_recorded"}'
print(sha256(event.encode("utf-8")).hexdigest())
PY
)"

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v canonical_event="${canonical_event}" \
    -v canonical_digest="${canonical_digest}" <<SQL
INSERT INTO job_analysis_snapshot (
    tenant_record_id, analysis_record_id, job_profile_id, position_record_id,
    criterion_blueprint_id, analysis_version_code, status_code, effective_from,
    recorded_at, reviewed_by_reference, reviewed_at, content_digest_sha256,
    data_function_code, people_function_code, things_function_code,
    fja_source_uri, fja_source_title, fja_source_version_code, fja_retrieved_at,
    fja_content_digest_sha256, fja_origin_code
) VALUES (
    '${TENANT_ID}', '${ANALYSIS_ID}', '${JOB_ID}', '${POSITION_ID}',
    '${CRITERION_ID}', 'clinical-psychologist:v1', 'analysis_validated',
    DATE '2026-08-01', TIMESTAMPTZ '2026-08-18 05:00:00+00',
    'keyverse_subject:01JCLINICALSME', TIMESTAMPTZ '2026-08-18 04:50:00+00',
    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    1, 0, 7,
    'https://www.dol.gov/agencies/oalj/PUBLIC/DOT/REFERENCES/DOTAPPB',
    'Dictionary of Occupational Titles Appendix B', 'dot:1991',
    TIMESTAMPTZ '2026-08-18 03:00:00+00',
    'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
    'authoritative_occupation_source'
);

INSERT INTO job_analysis_task_item (
    tenant_record_id, analysis_record_id, task_record_id, task_statement,
    importance_level, difficulty_level, source_uri, source_title,
    source_version_code, retrieved_at, content_digest_sha256, origin_code
) VALUES (
    '${TENANT_ID}', '${ANALYSIS_ID}', '${TASK_ID}',
    '표준화된 심리검사를 실시하고 결과를 해석하여 진단 가설을 정리한다.',
    5, 4, 'https://www.onetcenter.org/database.html',
    'O*NET 30.3 Clinical and Counseling Psychologists', 'onet:30.3',
    TIMESTAMPTZ '2026-08-18 03:00:00+00',
    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    'authoritative_occupation_source'
);

INSERT INTO job_analysis_ksao_item (
    tenant_record_id, analysis_record_id, ksao_record_id, category_code,
    requirement_statement, importance_level, proficiency_level, source_uri,
    source_title, source_version_code, retrieved_at, content_digest_sha256,
    origin_code
) VALUES (
    '${TENANT_ID}', '${ANALYSIS_ID}', '${KSAO_ID}', 'knowledge_requirement',
    'DSM-5-TR 진단 기준과 심리측정 이론에 대한 지식.', 5, 4,
    'https://www.onetcenter.org/database.html',
    'O*NET 30.3 Clinical and Counseling Psychologists', 'onet:30.3',
    TIMESTAMPTZ '2026-08-18 03:00:00+00',
    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    'authoritative_occupation_source'
);

INSERT INTO job_analysis_task_ksao_link (
    tenant_record_id, analysis_record_id, task_record_id, ksao_record_id,
    relationship_strength, essential_for_task
) VALUES (
    '${TENANT_ID}', '${ANALYSIS_ID}', '${TASK_ID}', '${KSAO_ID}', 5, TRUE
);

INSERT INTO job_analysis_write_command (
    tenant_record_id, write_command_id, analysis_record_id, idempotency_key,
    request_digest_sha256, actor_reference, purpose_code
) VALUES (
    '${TENANT_ID}', '${COMMAND_ID}', '${ANALYSIS_ID}',
    'idempotency-clinical-psych-01',
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'keyverse_subject:01JACTOROPAQUE', 'job_analysis_write'
);

SELECT record_audit_outbox_event(
    '${TENANT_ID}'::uuid, '${AUDIT_ID}'::uuid, '${OUTBOX_ID}'::uuid,
    :'canonical_event', :'canonical_digest', 'integration_hub'
);
SQL

task_statement="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT task_statement FROM job_analysis_task_item
WHERE analysis_record_id = '${ANALYSIS_ID}'::uuid;
")"
if [[ "${task_statement}" != *"표준화된 심리검사를 실시하고"* ]]; then
    echo "persisted task statement did not round-trip: ${task_statement}" >&2
    exit 1
fi

ksao_statement="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT requirement_statement FROM job_analysis_ksao_item
WHERE analysis_record_id = '${ANALYSIS_ID}'::uuid;
")"
if [[ "${ksao_statement}" != *"DSM-5-TR"* ]]; then
    echo "persisted KSAO statement did not round-trip: ${ksao_statement}" >&2
    exit 1
fi

idempotency_key="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT idempotency_key FROM job_analysis_write_command
WHERE analysis_record_id = '${ANALYSIS_ID}'::uuid;
")"
if [[ "${idempotency_key}" != "idempotency-clinical-psych-01" ]]; then
    echo "Idempotency-Key did not persist on the write command" >&2
    exit 1
fi

audit_count="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*) FROM audit_event_record
WHERE audit_event_record_id = '${AUDIT_ID}'::uuid;
")"
if [[ "${audit_count}" != "1" ]]; then
    echo "record_audit_outbox_event did not persist with the snapshot write" >&2
    exit 1
fi

set +e
update_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
    "UPDATE job_analysis_snapshot SET status_code = 'analysis_draft' WHERE analysis_record_id = '${ANALYSIS_ID}'::uuid;" ; } 2>&1)"
update_status=$?
set -e
if [[ ${update_status} -eq 0 || "${update_output}" != *"append-only"* ]]; then
    echo "job-analysis snapshot was mutable: ${update_output}" >&2
    exit 1
fi

set +e
delete_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
    "DELETE FROM job_analysis_snapshot WHERE analysis_record_id = '${ANALYSIS_ID}'::uuid;" ; } 2>&1)"
delete_status=$?
set -e
if [[ ${delete_status} -eq 0 || "${delete_output}" != *"append-only"* ]]; then
    echo "job-analysis snapshot was deletable: ${delete_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
DO $role$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'orgmetra_job_analysis_reader') THEN
        CREATE ROLE orgmetra_job_analysis_reader NOLOGIN NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$role$;
GRANT USAGE ON SCHEMA public TO orgmetra_job_analysis_reader;
GRANT SELECT ON job_analysis_snapshot TO orgmetra_job_analysis_reader;
SQL

other_tenant_rows="$(
    PGOPTIONS="-c orgmetra.tenant_record_id=${OTHER_TENANT_ID}" \
        psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc \
        "SET ROLE orgmetra_job_analysis_reader; SELECT count(*) FROM job_analysis_snapshot;"
)"
if [[ "${other_tenant_rows}" != "0" ]]; then
    echo "row-level security leaked job-analysis rows across tenants: ${other_tenant_rows}" >&2
    exit 1
fi

echo "job-analysis snapshot PostgreSQL contract passed"
