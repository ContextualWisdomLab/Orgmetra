#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0003_audit_outbox_persistence.sql \
    database/migrations/0013_job_analysis_snapshot.sql \
    database/migrations/0019_job_qualification_rule_persistence.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="10000000-0000-7000-8000-000000000001"
OTHER_TENANT_ID="20000000-0000-7000-8000-000000000002"
JOB_ID="00000000-0000-7000-8000-000000000021"
OTHER_JOB_ID="00000000-0000-7000-8000-000000000022"
ANALYSIS_ID="00000000-0000-7000-8000-000000000081"
OTHER_ANALYSIS_ID="00000000-0000-7000-8000-000000000082"
DRAFT_ANALYSIS_ID="00000000-0000-7000-8000-000000000083"
RULE_ID="00000000-0000-7000-8000-000000000091"
RULE_VERSION_ID="00000000-0000-7000-8000-000000000092"
AUDIT_ID="00000000-0000-4000-8000-000000000095"
OUTBOX_ID="00000000-0000-4000-8000-000000000096"
SNAPSHOT_DIGEST="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
OTHER_SNAPSHOT_DIGEST="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
RULE_DIGEST="dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
TASK_DIGEST="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
KSAO_DIGEST="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SOURCE_DIGEST="1111111111111111111111111111111111111111111111111111111111111111"
REVIEW_DIGEST="2222222222222222222222222222222222222222222222222222222222222222"
REVIEWER="actor:00000000-0000-4000-8000-000000000031"

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
    TIMESTAMPTZ '2026-08-22 22:00:00+00', '${SOURCE_DIGEST}', 'authoritative_occupation_source'
),
(
    '${TENANT_ID}', '${OTHER_ANALYSIS_ID}', '${OTHER_JOB_ID}', 'other:v1', 'analysis_validated',
    DATE '2026-08-01', TIMESTAMPTZ '2026-08-23 00:00:00+00', '${REVIEWER}',
    TIMESTAMPTZ '2026-08-22 23:00:00+00', '${OTHER_SNAPSHOT_DIGEST}', 1, 1, 1,
    'https://example.invalid/fja', 'Reviewed FJA evidence', 'v1',
    TIMESTAMPTZ '2026-08-22 22:00:00+00', '${SOURCE_DIGEST}', 'authoritative_occupation_source'
),
(
    '${TENANT_ID}', '${DRAFT_ANALYSIS_ID}', '${JOB_ID}', 'job:draft', 'analysis_draft',
    DATE '2026-08-01', TIMESTAMPTZ '2026-08-23 00:00:00+00', NULL, NULL,
    '${OTHER_SNAPSHOT_DIGEST}', 1, 1, 1,
    'https://example.invalid/fja', 'Draft FJA evidence', 'v1',
    TIMESTAMPTZ '2026-08-22 22:00:00+00', '${SOURCE_DIGEST}', 'authoritative_occupation_source'
);
SQL

canonical_event="$(python3 - <<PY
import json
payload = {
    "data": {"high_impact": False, "result_code": "reviewed_for_authoritative_activation"},
    "datacontenttype": "application/json",
    "id": "${AUDIT_ID}",
    "orgmetraactor": "${REVIEWER}",
    "orgmetraevidence": "${REVIEW_DIGEST}",
    "orgmetrapurpose": "job_qualification_rule_review",
    "orgmetrareason": "job_analysis_revision",
    "orgmetratenant": "${TENANT_ID}",
    "source": "urn:orgmetra:job_analysis_api",
    "specversion": "1.0",
    "subject": "job_qualification_rule:${RULE_ID}",
    "time": "2026-08-23T01:00:00Z",
    "type": "orgmetra.job_architecture.qualification_rule_reviewed",
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
    -v canonical_event="${canonical_event}" -v canonical_digest="${canonical_digest}" <<SQL
SELECT record_audit_outbox_event(
    '${TENANT_ID}'::uuid, '${AUDIT_ID}'::uuid, '${OUTBOX_ID}'::uuid,
    :'canonical_event', :'canonical_digest', 'integration_hub'
);

INSERT INTO job_qualification_rule_record (
    tenant_record_id, job_qualification_rule_record_id, job_profile_id
) VALUES ('${TENANT_ID}', '${RULE_ID}', '${JOB_ID}');

INSERT INTO job_qualification_rule_version (
    tenant_record_id, job_qualification_rule_version_id,
    job_qualification_rule_record_id, analysis_record_id, rule_category_code,
    qualification_rule_artifact_digest_sha256, job_analysis_snapshot_digest_sha256,
    task_linkage_digest_sha256, ksao_linkage_digest_sha256, source_evidence_digest_sha256,
    review_evidence_digest_sha256, reviewer_actor_reference, evidence_version,
    reviewed_at, effective_from, audit_event_record_id
) VALUES (
    '${TENANT_ID}', '${RULE_VERSION_ID}', '${RULE_ID}', '${ANALYSIS_ID}',
    'knowledge_skill_ability_requirement', '${RULE_DIGEST}', '${SNAPSHOT_DIGEST}',
    '${TASK_DIGEST}', '${KSAO_DIGEST}', '${SOURCE_DIGEST}', '${REVIEW_DIGEST}',
    '${REVIEWER}', 1, TIMESTAMPTZ '2026-08-23 01:00:00+00',
    DATE '2026-08-25', '${AUDIT_ID}'
);
SQL

state="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "
SELECT activation_state || '|' || decision_authority_state
FROM job_qualification_rule_version
WHERE job_qualification_rule_version_id = '${RULE_VERSION_ID}'::uuid;
")"
if [[ "${state}" != "requires_authoritative_activation|not_authorized_for_candidate_or_employment_decision" ]]; then
    echo "qualification rule persisted an unsafe governance state: ${state}" >&2
    exit 1
fi

set +e
mismatch_output="$({ with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO job_qualification_rule_version (
    tenant_record_id, job_qualification_rule_version_id, job_qualification_rule_record_id,
    analysis_record_id, rule_category_code, qualification_rule_artifact_digest_sha256,
    job_analysis_snapshot_digest_sha256, task_linkage_digest_sha256,
    ksao_linkage_digest_sha256, source_evidence_digest_sha256,
    review_evidence_digest_sha256, reviewer_actor_reference, evidence_version,
    reviewed_at, effective_from, audit_event_record_id
) VALUES (
    '${TENANT_ID}', '00000000-0000-7000-8000-000000000099', '${RULE_ID}',
    '${OTHER_ANALYSIS_ID}', 'experience_requirement', '${RULE_DIGEST}',
    '${OTHER_SNAPSHOT_DIGEST}', '${TASK_DIGEST}', '${KSAO_DIGEST}', '${SOURCE_DIGEST}',
    '${REVIEW_DIGEST}', '${REVIEWER}', 2, TIMESTAMPTZ '2026-08-23 01:00:00+00',
    DATE '2026-09-01', '${AUDIT_ID}'
);" ; } 2>&1)"
mismatch_status=$?
set -e
if [[ ${mismatch_status} -eq 0 || "${mismatch_output}" != *"same Job"* ]]; then
    echo "qualification rule accepted a Job Analysis snapshot from another Job: ${mismatch_output}" >&2
    exit 1
fi

set +e
draft_output="$({ with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO job_qualification_rule_version (
    tenant_record_id, job_qualification_rule_version_id, job_qualification_rule_record_id,
    analysis_record_id, rule_category_code, qualification_rule_artifact_digest_sha256,
    job_analysis_snapshot_digest_sha256, task_linkage_digest_sha256,
    ksao_linkage_digest_sha256, source_evidence_digest_sha256,
    review_evidence_digest_sha256, reviewer_actor_reference, evidence_version,
    reviewed_at, effective_from, audit_event_record_id
) VALUES (
    '${TENANT_ID}', '00000000-0000-7000-8000-000000000100', '${RULE_ID}',
    '${DRAFT_ANALYSIS_ID}', 'experience_requirement', '${RULE_DIGEST}',
    '${OTHER_SNAPSHOT_DIGEST}', '${TASK_DIGEST}', '${KSAO_DIGEST}', '${SOURCE_DIGEST}',
    '${REVIEW_DIGEST}', '${REVIEWER}', 2, TIMESTAMPTZ '2026-08-23 01:00:00+00',
    DATE '2026-09-01', '${AUDIT_ID}'
);" ; } 2>&1)"
draft_status=$?
set -e
if [[ ${draft_status} -eq 0 || "${draft_output}" != *"validated Job Analysis"* ]]; then
    echo "qualification rule accepted an unvalidated Job Analysis snapshot: ${draft_output}" >&2
    exit 1
fi

set +e
backdated_output="$({ with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO job_qualification_rule_record (
    tenant_record_id, job_qualification_rule_record_id, job_profile_id, recorded_from
) VALUES (
    '${TENANT_ID}', '00000000-0000-7000-8000-000000000101', '${JOB_ID}',
    TIMESTAMPTZ '2000-01-01 00:00:00+00'
);" ; } 2>&1)"
backdated_status=$?
set -e
if [[ ${backdated_status} -eq 0 || "${backdated_output}" != *"transaction timestamp"* ]]; then
    echo "qualification-rule anchor accepted caller-backdated system time: ${backdated_output}" >&2
    exit 1
fi

set +e
rewrite_output="$({ with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
UPDATE job_qualification_rule_version
SET rule_category_code = 'experience_requirement'
WHERE job_qualification_rule_version_id = '${RULE_VERSION_ID}'::uuid;" ; } 2>&1)"
rewrite_status=$?
set -e
if [[ ${rewrite_status} -eq 0 || "${rewrite_output}" != *"history"* ]]; then
    echo "qualification-rule recorded evidence was rewriteable: ${rewrite_output}" >&2
    exit 1
fi

set +e
truncate_output="$({ with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
    "TRUNCATE job_qualification_rule_version;" ; } 2>&1)"
truncate_status=$?
set -e
if [[ ${truncate_status} -eq 0 || "${truncate_output}" != *"cannot be truncated"* ]]; then
    echo "qualification-rule evidence could be truncated: ${truncate_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'orgmetra_rule_reader') THEN
        CREATE ROLE orgmetra_rule_reader LOGIN PASSWORD 'orgmetra_rule_reader' NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;
GRANT CONNECT ON DATABASE orgmetra TO orgmetra_rule_reader;
GRANT USAGE ON SCHEMA public TO orgmetra_rule_reader;
GRANT SELECT ON job_qualification_rule_record, job_qualification_rule_version TO orgmetra_rule_reader;
SQL

alpha_count="$(PGPASSWORD=orgmetra_rule_reader PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
    psql -h localhost -U orgmetra_rule_reader -d orgmetra -Atqc \
    'SELECT count(*) FROM job_qualification_rule_version;')"
beta_count="$(PGPASSWORD=orgmetra_rule_reader PGOPTIONS="-c orgmetra.tenant_record_id=${OTHER_TENANT_ID}" \
    psql -h localhost -U orgmetra_rule_reader -d orgmetra -Atqc \
    'SELECT count(*) FROM job_qualification_rule_version;')"
missing_count="$(PGPASSWORD=orgmetra_rule_reader \
    psql -h localhost -U orgmetra_rule_reader -d orgmetra -Atqc \
    'SELECT count(*) FROM job_qualification_rule_version;')"

if [[ "${alpha_count}" != "1" || "${beta_count}" != "0" || "${missing_count}" != "0" ]]; then
    echo "qualification-rule RLS isolation failed: alpha=${alpha_count} beta=${beta_count} missing=${missing_count}" >&2
    exit 1
fi

echo "job qualification-rule persistence contract passed"
