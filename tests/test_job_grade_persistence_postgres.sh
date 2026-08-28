#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0003_audit_outbox_persistence.sql \
    database/migrations/0013_job_analysis_snapshot.sql \
    database/migrations/0022_job_grade_persistence.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="10000000-0000-7000-8000-000000000001"
OTHER_TENANT_ID="20000000-0000-7000-8000-000000000002"
JOB_ID="00000000-0000-7000-8000-000000000021"
OTHER_JOB_ID="00000000-0000-7000-8000-000000000022"
ANALYSIS_ID="00000000-0000-7000-8000-000000000081"
OTHER_ANALYSIS_ID="00000000-0000-7000-8000-000000000082"
GRADE_DEFINITION_ID="00000000-0000-7000-8000-000000000091"
OTHER_GRADE_DEFINITION_ID="00000000-0000-7000-8000-000000000092"
ASSIGNMENT_ID="00000000-0000-7000-8000-000000000093"
ASSIGNMENT_VERSION_ID="00000000-0000-7000-8000-000000000094"
AUDIT_ID="00000000-0000-4000-8000-000000000095"
OUTBOX_ID="00000000-0000-4000-8000-000000000096"
SNAPSHOT_DIGEST="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
OTHER_SNAPSHOT_DIGEST="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
METHOD_DIGEST="dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
GRADE_DEFINITION_DIGEST="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
OTHER_GRADE_DEFINITION_DIGEST="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
REVIEWER="actor:00000000-0000-4000-8000-000000000031"
REQUESTER="actor:00000000-0000-4000-8000-000000000032"
REASON_CODE="job_architecture_alignment"
REVIEWED_AT="2026-08-23T01:00:00Z"
PACKET_RECORDED_AT="2026-08-23T01:01:00Z"
NEXT_ACTION="Within tenant_record_id, re-resolve the authoritative Job and persisted Job Analysis snapshot, verify their exact evidence digest and the reviewed enterprise grade/band definition digest, confirm accountable reviewer authority and human review, then persist any bitemporal Job-grade fact with immutable audit/outbox evidence. This packet does not mutate Job, Position, Assignment, compensation, or any employment decision."

with_tenant() {
    local tenant="$1"
    shift
    PGOPTIONS="-c orgmetra.tenant_record_id=${tenant}" command psql "$@"
}

with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}', 'tenant_alpha'), ('${OTHER_TENANT_ID}', 'tenant_beta');

INSERT INTO job_profile (tenant_record_id, job_profile_id)
VALUES
    ('${TENANT_ID}', '${JOB_ID}'),
    ('${TENANT_ID}', '${OTHER_JOB_ID}');

INSERT INTO job_analysis_snapshot (
    tenant_record_id, analysis_record_id, job_profile_id, analysis_version_code,
    status_code, effective_from, recorded_at, reviewed_by_reference, reviewed_at,
    content_digest_sha256, data_function_code, people_function_code, things_function_code,
    fja_source_uri, fja_source_title, fja_source_version_code, fja_retrieved_at,
    fja_content_digest_sha256, fja_origin_code
) VALUES
(
    '${TENANT_ID}', '${ANALYSIS_ID}', '${JOB_ID}', 'job:v1', 'analysis_validated',
    DATE '2026-08-01', TIMESTAMPTZ '2026-08-23 00:00:00+00', '${REVIEWER}',
    TIMESTAMPTZ '2026-08-22 23:00:00+00', '${SNAPSHOT_DIGEST}', 1, 1, 1,
    'https://example.invalid/fja', 'Reviewed FJA evidence', 'v1',
    TIMESTAMPTZ '2026-08-22 22:00:00+00', '${SNAPSHOT_DIGEST}',
    'authoritative_occupation_source'
),
(
    '${TENANT_ID}', '${OTHER_ANALYSIS_ID}', '${OTHER_JOB_ID}', 'other:v1', 'analysis_validated',
    DATE '2026-08-01', TIMESTAMPTZ '2026-08-23 00:00:00+00', '${REVIEWER}',
    TIMESTAMPTZ '2026-08-22 23:00:00+00', '${OTHER_SNAPSHOT_DIGEST}', 1, 1, 1,
    'https://example.invalid/fja', 'Reviewed FJA evidence', 'v1',
    TIMESTAMPTZ '2026-08-22 22:00:00+00', '${OTHER_SNAPSHOT_DIGEST}',
    'authoritative_occupation_source'
);
SQL

review_evidence="$(python3 - <<PY
import json
payload = {
    "band_code": "B2",
    "decision_authority": "not_authorized_to_assign_grade_or_compensation",
    "evidence_version": 1,
    "grade_band_definition_digest": "${GRADE_DEFINITION_DIGEST}",
    "grade_code": "G5",
    "human_review_required": True,
    "job_analysis_snapshot_digest": "${SNAPSHOT_DIGEST}",
    "job_analysis_snapshot_reference": "job_analysis_snapshot:${ANALYSIS_ID}",
    "job_evaluation_method_code": "factor_evaluation_method",
    "job_evaluation_method_digest": "${METHOD_DIGEST}",
    "job_record_reference": "job_record:${JOB_ID}",
    "next_action": "${NEXT_ACTION}",
    "purpose_code": "job_grade_design_review",
    "reason_code": "${REASON_CODE}",
    "recorded_at": "${PACKET_RECORDED_AT}",
    "requester_actor_reference": "${REQUESTER}",
    "review_state": "reviewed_for_authoritative_resolution",
    "reviewed_at": "${REVIEWED_AT}",
    "reviewer_actor_reference": "${REVIEWER}",
    "tenant_record_id": "${TENANT_ID}",
}
print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
PY
)"
review_digest="$(REVIEW_EVIDENCE="${review_evidence}" python3 - <<'PY'
from hashlib import sha256
import os
print(sha256(os.environ["REVIEW_EVIDENCE"].encode("utf-8")).hexdigest())
PY
)"

canonical_event="$(python3 - <<PY
import json
payload = {
    "data": {"high_impact": False, "result_code": "reviewed_for_authoritative_resolution"},
    "datacontenttype": "application/json",
    "id": "${AUDIT_ID}",
    "orgmetraactor": "${REVIEWER}",
    "orgmetraevidence": "${review_digest}",
    "orgmetrapurpose": "job_grade_design_review",
    "orgmetrareason": "${REASON_CODE}",
    "orgmetratenant": "${TENANT_ID}",
    "source": "urn:orgmetra:job_architecture",
    "specversion": "1.0",
    "subject": "job_grade_assignment:${ASSIGNMENT_ID}",
    "time": "${REVIEWED_AT}",
    "type": "orgmetra.job_architecture.grade_design_reviewed",
}
print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
PY
)"
canonical_digest="$(CANONICAL_EVENT="${canonical_event}" python3 - <<'PY'
from hashlib import sha256
import os
print(sha256(os.environ["CANONICAL_EVENT"].encode("utf-8")).hexdigest())
PY
)"

with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v canonical_event="${canonical_event}" -v canonical_digest="${canonical_digest}" \
    -v review_evidence="${review_evidence}" -v review_digest="${review_digest}" <<SQL
SELECT record_audit_outbox_event(
    '${TENANT_ID}'::uuid, '${AUDIT_ID}'::uuid, '${OUTBOX_ID}'::uuid,
    :'canonical_event', :'canonical_digest', 'integration_hub'
);

INSERT INTO job_grade_definition_record (
    tenant_record_id, job_grade_definition_record_id,
    grade_code, band_code, grade_band_definition_digest_sha256
) VALUES (
    '${TENANT_ID}', '${GRADE_DEFINITION_ID}', 'G5', 'B2', '${GRADE_DEFINITION_DIGEST}'
), (
    '${TENANT_ID}', '${OTHER_GRADE_DEFINITION_ID}', 'G6', 'B3', '${OTHER_GRADE_DEFINITION_DIGEST}'
);

INSERT INTO job_grade_assignment_record (
    tenant_record_id, job_grade_assignment_record_id, job_profile_id
) VALUES ('${TENANT_ID}', '${ASSIGNMENT_ID}', '${JOB_ID}');

INSERT INTO job_grade_assignment_version (
    tenant_record_id, job_grade_assignment_version_id,
    job_grade_assignment_record_id, job_grade_definition_record_id,
    analysis_record_id, job_analysis_snapshot_digest_sha256,
    job_evaluation_method_code, job_evaluation_method_digest_sha256,
    review_evidence_json, review_evidence_digest_sha256,
    requester_actor_reference, reviewer_actor_reference, reason_code, evidence_version,
    reviewed_at, review_packet_recorded_at, effective_from,
    audit_event_record_id
) VALUES (
    '${TENANT_ID}', '${ASSIGNMENT_VERSION_ID}', '${ASSIGNMENT_ID}',
    '${GRADE_DEFINITION_ID}', '${ANALYSIS_ID}', '${SNAPSHOT_DIGEST}',
    'factor_evaluation_method', '${METHOD_DIGEST}', :'review_evidence', :'review_digest',
    '${REQUESTER}', '${REVIEWER}', '${REASON_CODE}', 1,
    TIMESTAMPTZ '${REVIEWED_AT}', TIMESTAMPTZ '${PACKET_RECORDED_AT}',
    DATE '2026-09-01', '${AUDIT_ID}'
);
SQL

state="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "
SELECT job_architecture_state || '|' || decision_authority_state
FROM job_grade_assignment_version
WHERE job_grade_assignment_version_id = '${ASSIGNMENT_VERSION_ID}'::uuid;
")"
if [[ "${state}" != "authoritative_job_grade_assignment|not_authorized_for_compensation_or_employment_decision" ]]; then
    echo "Job grade assignment persisted unsafe governance state: ${state}" >&2
    exit 1
fi

trusted_search_path_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM pg_proc AS procedure_record
JOIN pg_namespace AS namespace_record
  ON namespace_record.oid = procedure_record.pronamespace
WHERE namespace_record.nspname = 'public'
  AND procedure_record.proname IN (
      'enforce_job_grade_definition_system_time',
      'enforce_job_grade_assignment_system_time',
      'protect_job_grade_definition_immutability',
      'protect_job_grade_assignment_history',
      'enforce_job_grade_assignment_scope',
      'enforce_job_grade_assignment_anchor_alignment',
      'reject_job_grade_persistence_truncate'
  )
  AND procedure_record.proconfig @> ARRAY['search_path=pg_catalog, public, pg_temp']::text[];")"
if [[ "${trusted_search_path_count}" != "7" ]]; then
    echo "Job grade trigger functions do not pin the trusted search_path: ${trusted_search_path_count}/7" >&2
    exit 1
fi

set +e
mismatch_output="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v review_evidence="${review_evidence}" -v review_digest="${review_digest}" <<SQL 2>&1
INSERT INTO job_grade_assignment_version (
    tenant_record_id, job_grade_assignment_version_id,
    job_grade_assignment_record_id, job_grade_definition_record_id,
    analysis_record_id, job_analysis_snapshot_digest_sha256,
    job_evaluation_method_code, job_evaluation_method_digest_sha256,
    review_evidence_json, review_evidence_digest_sha256,
    requester_actor_reference, reviewer_actor_reference, reason_code, evidence_version,
    reviewed_at, review_packet_recorded_at, effective_from, audit_event_record_id
) VALUES (
    '${TENANT_ID}', '00000000-0000-7000-8000-000000000097', '${ASSIGNMENT_ID}',
    '${OTHER_GRADE_DEFINITION_ID}', '${ANALYSIS_ID}', '${SNAPSHOT_DIGEST}',
    'factor_evaluation_method', '${METHOD_DIGEST}', :'review_evidence', :'review_digest',
    '${REQUESTER}', '${REVIEWER}', '${REASON_CODE}', 1,
    TIMESTAMPTZ '${REVIEWED_AT}', TIMESTAMPTZ '${PACKET_RECORDED_AT}',
    DATE '2027-01-01', '${AUDIT_ID}'
);
SQL
)"
mismatch_status=$?
set -e
if [[ ${mismatch_status} -eq 0 || "${mismatch_output}" != *"canonical Job grade review evidence"* ]]; then
    echo "Job grade assignment accepted evidence for a different grade definition: ${mismatch_output}" >&2
    exit 1
fi

set +e
wrong_job_output="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v review_evidence="${review_evidence}" -v review_digest="${review_digest}" <<SQL 2>&1
INSERT INTO job_grade_assignment_version (
    tenant_record_id, job_grade_assignment_version_id,
    job_grade_assignment_record_id, job_grade_definition_record_id,
    analysis_record_id, job_analysis_snapshot_digest_sha256,
    job_evaluation_method_code, job_evaluation_method_digest_sha256,
    review_evidence_json, review_evidence_digest_sha256,
    requester_actor_reference, reviewer_actor_reference, reason_code, evidence_version,
    reviewed_at, review_packet_recorded_at, effective_from, audit_event_record_id
) VALUES (
    '${TENANT_ID}', '00000000-0000-7000-8000-000000000098', '${ASSIGNMENT_ID}',
    '${GRADE_DEFINITION_ID}', '${OTHER_ANALYSIS_ID}', '${OTHER_SNAPSHOT_DIGEST}',
    'factor_evaluation_method', '${METHOD_DIGEST}', :'review_evidence', :'review_digest',
    '${REQUESTER}', '${REVIEWER}', '${REASON_CODE}', 1,
    TIMESTAMPTZ '${REVIEWED_AT}', TIMESTAMPTZ '${PACKET_RECORDED_AT}',
    DATE '2027-01-01', '${AUDIT_ID}'
);
SQL
)"
wrong_job_status=$?
set -e
if [[ ${wrong_job_status} -eq 0 || "${wrong_job_output}" != *"same Job"* ]]; then
    echo "Job grade assignment accepted a Job Analysis snapshot from another Job: ${wrong_job_output}" >&2
    exit 1
fi

set +e
backdated_output="$({ with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO job_grade_assignment_record (
    tenant_record_id, job_grade_assignment_record_id, job_profile_id, recorded_from
) VALUES (
    '${TENANT_ID}', '00000000-0000-7000-8000-000000000099', '${OTHER_JOB_ID}',
    TIMESTAMPTZ '2000-01-01 00:00:00+00'
);" ; } 2>&1)"
backdated_status=$?
set -e
if [[ ${backdated_status} -eq 0 || "${backdated_output}" != *"transaction timestamp"* ]]; then
    echo "Job grade assignment anchor accepted caller-backdated system time: ${backdated_output}" >&2
    exit 1
fi

set +e
rewrite_output="$({ with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
UPDATE job_grade_assignment_version
SET job_evaluation_method_code = 'different_method_code'
WHERE job_grade_assignment_version_id = '${ASSIGNMENT_VERSION_ID}'::uuid;" ; } 2>&1)"
rewrite_status=$?
set -e
if [[ ${rewrite_status} -eq 0 || "${rewrite_output}" != *"history"* ]]; then
    echo "Job grade assignment evidence was rewriteable: ${rewrite_output}" >&2
    exit 1
fi

set +e
definition_rewrite_output="$({ with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
UPDATE job_grade_definition_record
SET grade_code = 'G9'
WHERE job_grade_definition_record_id = '${GRADE_DEFINITION_ID}'::uuid;" ; } 2>&1)"
definition_rewrite_status=$?
set -e
if [[ ${definition_rewrite_status} -eq 0 || "${definition_rewrite_output}" != *"immutable"* ]]; then
    echo "Job grade definition was rewriteable: ${definition_rewrite_output}" >&2
    exit 1
fi

set +e
truncate_output="$({ with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
    "TRUNCATE job_grade_assignment_version;" ; } 2>&1)"
truncate_status=$?
set -e
if [[ ${truncate_status} -eq 0 || "${truncate_output}" != *"cannot be truncated"* ]]; then
    echo "Job grade assignment evidence could be truncated: ${truncate_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'orgmetra_job_grade_reader') THEN
        CREATE ROLE orgmetra_job_grade_reader LOGIN PASSWORD 'orgmetra_job_grade_reader' NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;
GRANT CONNECT ON DATABASE orgmetra TO orgmetra_job_grade_reader;
GRANT USAGE ON SCHEMA public TO orgmetra_job_grade_reader;
GRANT SELECT ON job_grade_definition_record, job_grade_assignment_record, job_grade_assignment_version TO orgmetra_job_grade_reader;
SQL

alpha_count="$(PGPASSWORD=orgmetra_job_grade_reader PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
    psql -h localhost -U orgmetra_job_grade_reader -d orgmetra -Atqc \
    'SELECT count(*) FROM job_grade_assignment_version;')"
beta_count="$(PGPASSWORD=orgmetra_job_grade_reader PGOPTIONS="-c orgmetra.tenant_record_id=${OTHER_TENANT_ID}" \
    psql -h localhost -U orgmetra_job_grade_reader -d orgmetra -Atqc \
    'SELECT count(*) FROM job_grade_assignment_version;')"
missing_count="$(PGPASSWORD=orgmetra_job_grade_reader \
    psql -h localhost -U orgmetra_job_grade_reader -d orgmetra -Atqc \
    'SELECT count(*) FROM job_grade_assignment_version;')"

if [[ "${alpha_count}" != "1" || "${beta_count}" != "0" || "${missing_count}" != "0" ]]; then
    echo "Job grade persistence RLS isolation failed: alpha=${alpha_count} beta=${beta_count} missing=${missing_count}" >&2
    exit 1
fi

echo "Job grade persistence contract passed"
