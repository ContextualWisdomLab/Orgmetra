#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0003_audit_outbox_persistence.sql \
    database/migrations/0020_position_reporting_relationship.sql; do
    if [[ ! -f "${migration}" ]]; then
        echo "required position-reporting persistence migration is missing: ${migration}" >&2
        exit 1
    fi
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="10000000-0000-7000-8000-000000000001"
OTHER_TENANT_ID="20000000-0000-7000-8000-000000000002"
ORG_ID="00000000-0000-7000-8000-000000000011"
JOB_ID="00000000-0000-7000-8000-000000000021"
SUBORDINATE_POSITION_ID="00000000-0000-7000-8000-000000000031"
MANAGER_POSITION_ID="00000000-0000-7000-8000-000000000032"
OTHER_POSITION_ID="00000000-0000-7000-8000-000000000033"
RELATIONSHIP_ID="00000000-0000-7000-8000-000000000041"
RELATIONSHIP_VERSION_ID="00000000-0000-7000-8000-000000000042"
REVERSE_RELATIONSHIP_ID="00000000-0000-7000-8000-000000000043"
SELF_RELATIONSHIP_ID="00000000-0000-7000-8000-000000000044"
AUDIT_ID="00000000-0000-4000-8000-000000000051"
OUTBOX_ID="00000000-0000-4000-8000-000000000052"
REVIEWER="actor:00000000-0000-4000-8000-000000000061"
APPLIED_BY="actor:00000000-0000-4000-8000-000000000062"
REVIEW_DIGEST="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

with_tenant() {
    local tenant="$1"
    shift
    PGOPTIONS="-c orgmetra.tenant_record_id=${tenant}" command psql "$@"
}

expect_failure() {
    local label="$1"
    local needle="$2"
    local sql="$3"
    local output status
    set +e
    output="$({ with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "${sql}"; } 2>&1)"
    status=$?
    set -e
    if [[ ${status} -eq 0 || "${output}" != *"${needle}"* ]]; then
        echo "${label}: ${output}" >&2
        exit 1
    fi
}

with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}', 'tenant_alpha'), ('${OTHER_TENANT_ID}', 'tenant_beta');
INSERT INTO organization_unit (tenant_record_id, organization_unit_id)
VALUES ('${TENANT_ID}', '${ORG_ID}');
INSERT INTO job_profile (tenant_record_id, job_profile_id)
VALUES ('${TENANT_ID}', '${JOB_ID}');
INSERT INTO position_record (
    tenant_record_id, position_record_id, organization_unit_id, job_profile_id
) VALUES
    ('${TENANT_ID}', '${SUBORDINATE_POSITION_ID}', '${ORG_ID}', '${JOB_ID}'),
    ('${TENANT_ID}', '${MANAGER_POSITION_ID}', '${ORG_ID}', '${JOB_ID}'),
    ('${TENANT_ID}', '${OTHER_POSITION_ID}', '${ORG_ID}', '${JOB_ID}');
SQL

canonical_event="$(python3 - <<PY
import json
payload = {
    "data": {"high_impact": False, "result_code": "position_reporting_applied"},
    "datacontenttype": "application/json",
    "id": "${AUDIT_ID}",
    "orgmetraactor": "${APPLIED_BY}",
    "orgmetraevidence": "${REVIEW_DIGEST}",
    "orgmetrapurpose": "position_reporting_change_apply",
    "orgmetrareason": "approved_reporting_line_change",
    "orgmetratenant": "${TENANT_ID}",
    "source": "urn:orgmetra:people_api",
    "specversion": "1.0",
    "subject": "position_reporting_relationship:${RELATIONSHIP_ID}",
    "time": "2026-08-24T02:00:00Z",
    "type": "orgmetra.organization.position_reporting_applied",
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
INSERT INTO position_reporting_relationship_record (
    tenant_record_id, position_reporting_relationship_record_id,
    subordinate_position_record_id, relationship_type_code
) VALUES
    ('${TENANT_ID}', '${RELATIONSHIP_ID}', '${SUBORDINATE_POSITION_ID}', 'solid_line'),
    ('${TENANT_ID}', '${REVERSE_RELATIONSHIP_ID}', '${MANAGER_POSITION_ID}', 'solid_line'),
    ('${TENANT_ID}', '${SELF_RELATIONSHIP_ID}', '${OTHER_POSITION_ID}', 'solid_line');
INSERT INTO position_reporting_relationship_version (
    tenant_record_id, position_reporting_relationship_version_id,
    position_reporting_relationship_record_id, manager_position_record_id,
    review_evidence_digest_sha256, application_evidence_digest_sha256,
    reviewer_actor_reference, applied_by_actor_reference, reviewed_at,
    effective_from, audit_event_record_id
) VALUES (
    '${TENANT_ID}', '${RELATIONSHIP_VERSION_ID}', '${RELATIONSHIP_ID}',
    '${MANAGER_POSITION_ID}', '${REVIEW_DIGEST}', :'canonical_digest',
    '${REVIEWER}', '${APPLIED_BY}', TIMESTAMPTZ '2026-08-24 01:55:00+00',
    DATE '2026-08-24', '${AUDIT_ID}'
);
SQL

persisted="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "
SELECT relationship_type_code || '|' || manager_position_record_id::text || '|' || application_state
FROM position_reporting_relationship_record AS record
JOIN position_reporting_relationship_version AS version
  USING (tenant_record_id, position_reporting_relationship_record_id)
WHERE record.position_reporting_relationship_record_id = '${RELATIONSHIP_ID}'::uuid;
")"
if [[ "${persisted}" != "solid_line|${MANAGER_POSITION_ID}|applied_after_human_review" ]]; then
    echo "position-reporting relationship persisted unsafe or incomplete evidence: ${persisted}" >&2
    exit 1
fi

expect_failure \
    "position-reporting anchor accepted caller-backdated system time" \
    "transaction timestamp" \
    "INSERT INTO position_reporting_relationship_record (
        tenant_record_id, position_reporting_relationship_record_id,
        subordinate_position_record_id, relationship_type_code, recorded_from
     ) VALUES (
        '${TENANT_ID}', '00000000-0000-7000-8000-000000000071',
        '${SUBORDINATE_POSITION_ID}', 'solid_line', TIMESTAMPTZ '2000-01-01 00:00:00+00'
     );"

version_columns="tenant_record_id, position_reporting_relationship_version_id,
position_reporting_relationship_record_id, manager_position_record_id,
review_evidence_digest_sha256, application_evidence_digest_sha256,
reviewer_actor_reference, applied_by_actor_reference, reviewed_at,
effective_from, audit_event_record_id"

expect_failure \
    "position-reporting relationship accepted self-reporting" \
    "cannot report to itself" \
    "INSERT INTO position_reporting_relationship_version (${version_columns}) VALUES (
        '${TENANT_ID}', '00000000-0000-7000-8000-000000000072',
        '${SELF_RELATIONSHIP_ID}', '${OTHER_POSITION_ID}',
        '${REVIEW_DIGEST}', '${canonical_digest}', '${REVIEWER}', '${APPLIED_BY}',
        TIMESTAMPTZ '2026-08-24 01:55:00+00', DATE '2026-08-24', '${AUDIT_ID}'
     );"

expect_failure \
    "position-reporting relationship accepted a management cycle" \
    "cycle" \
    "INSERT INTO position_reporting_relationship_version (${version_columns}) VALUES (
        '${TENANT_ID}', '00000000-0000-7000-8000-000000000073',
        '${REVERSE_RELATIONSHIP_ID}', '${SUBORDINATE_POSITION_ID}',
        '${REVIEW_DIGEST}', '${canonical_digest}', '${REVIEWER}', '${APPLIED_BY}',
        TIMESTAMPTZ '2026-08-24 01:55:00+00', DATE '2026-08-24', '${AUDIT_ID}'
     );"

expect_failure \
    "position-reporting history was rewriteable" \
    "history" \
    "UPDATE position_reporting_relationship_version
     SET manager_position_record_id = '${OTHER_POSITION_ID}'::uuid
     WHERE position_reporting_relationship_version_id = '${RELATIONSHIP_VERSION_ID}'::uuid;"

expect_failure \
    "position-reporting history could be truncated" \
    "cannot be truncated" \
    "TRUNCATE position_reporting_relationship_version;"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'orgmetra_reporting_reader') THEN
        CREATE ROLE orgmetra_reporting_reader LOGIN PASSWORD 'orgmetra_reporting_reader' NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;
GRANT CONNECT ON DATABASE orgmetra TO orgmetra_reporting_reader;
GRANT USAGE ON SCHEMA public TO orgmetra_reporting_reader;
GRANT SELECT ON position_reporting_relationship_record, position_reporting_relationship_version TO orgmetra_reporting_reader;
SQL

alpha_count="$(PGPASSWORD=orgmetra_reporting_reader PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
    psql -h localhost -U orgmetra_reporting_reader -d orgmetra -Atqc \
    'SELECT count(*) FROM position_reporting_relationship_version;')"
beta_count="$(PGPASSWORD=orgmetra_reporting_reader PGOPTIONS="-c orgmetra.tenant_record_id=${OTHER_TENANT_ID}" \
    psql -h localhost -U orgmetra_reporting_reader -d orgmetra -Atqc \
    'SELECT count(*) FROM position_reporting_relationship_version;')"
missing_count="$(PGPASSWORD=orgmetra_reporting_reader \
    psql -h localhost -U orgmetra_reporting_reader -d orgmetra -Atqc \
    'SELECT count(*) FROM position_reporting_relationship_version;')"
if [[ "${alpha_count}" != "1" || "${beta_count}" != "0" || "${missing_count}" != "0" ]]; then
    echo "position-reporting RLS isolation failed: alpha=${alpha_count} beta=${beta_count} missing=${missing_count}" >&2
    exit 1
fi

echo "position-reporting persistence contract passed"
