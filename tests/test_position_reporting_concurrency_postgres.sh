#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
TENANT_ID="10000000-0000-7000-8000-000000000001"
ORG_ID="00000000-0000-7000-8000-000000000011"
JOB_ID="00000000-0000-7000-8000-000000000021"
POSITION_X="00000000-0000-7000-8000-000000000081"
POSITION_Y="00000000-0000-7000-8000-000000000082"
REL_X="00000000-0000-7000-8000-000000000083"
REL_Y="00000000-0000-7000-8000-000000000084"
VERSION_X="00000000-0000-7000-8000-000000000085"
VERSION_Y="00000000-0000-7000-8000-000000000086"
AUDIT_X="00000000-0000-4000-8000-000000000087"
AUDIT_Y="00000000-0000-4000-8000-000000000088"
OUTBOX_X="00000000-0000-4000-8000-000000000089"
OUTBOX_Y="00000000-0000-4000-8000-000000000090"
REVIEWER_X="actor:00000000-0000-4000-8000-000000000091"
REVIEWER_Y="actor:00000000-0000-4000-8000-000000000092"
APPLIER_X="actor:00000000-0000-4000-8000-000000000093"
APPLIER_Y="actor:00000000-0000-4000-8000-000000000094"
REVIEW_DIGEST_X="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
REVIEW_DIGEST_Y="dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"

with_tenant() {
    local tenant="$1"
    shift
    PGOPTIONS="-c orgmetra.tenant_record_id=${tenant}" command psql "$@"
}

with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO position_record (
    tenant_record_id, position_record_id, organization_unit_id, job_profile_id
) VALUES
    ('${TENANT_ID}', '${POSITION_X}', '${ORG_ID}', '${JOB_ID}'),
    ('${TENANT_ID}', '${POSITION_Y}', '${ORG_ID}', '${JOB_ID}');
INSERT INTO position_reporting_relationship_record (
    tenant_record_id, position_reporting_relationship_record_id,
    subordinate_position_record_id, relationship_type_code
) VALUES
    ('${TENANT_ID}', '${REL_X}', '${POSITION_X}', 'solid_line'),
    ('${TENANT_ID}', '${REL_Y}', '${POSITION_Y}', 'solid_line');
SQL

make_event() {
    local audit_id="$1" actor="$2" review_digest="$3" relationship_id="$4"
    AUDIT_ID="${audit_id}" ACTOR="${actor}" REVIEW_DIGEST="${review_digest}" RELATIONSHIP_ID="${relationship_id}" \
    python3 - <<'PY'
import json, os
payload = {
    "data": {"high_impact": False, "result_code": "position_reporting_applied"},
    "datacontenttype": "application/json",
    "id": os.environ["AUDIT_ID"],
    "orgmetraactor": os.environ["ACTOR"],
    "orgmetraevidence": os.environ["REVIEW_DIGEST"],
    "orgmetrapurpose": "position_reporting_change_apply",
    "orgmetrareason": "approved_reporting_line_change",
    "orgmetratenant": "10000000-0000-7000-8000-000000000001",
    "source": "urn:orgmetra:people_api",
    "specversion": "1.0",
    "subject": "position_reporting_relationship:" + os.environ["RELATIONSHIP_ID"],
    "time": "2026-08-24T02:00:00Z",
    "type": "orgmetra.organization.position_reporting_applied",
}
print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
PY
}

event_x="$(make_event "${AUDIT_X}" "${APPLIER_X}" "${REVIEW_DIGEST_X}" "${REL_X}")"
event_y="$(make_event "${AUDIT_Y}" "${APPLIER_Y}" "${REVIEW_DIGEST_Y}" "${REL_Y}")"
digest_x="$(EVENT="${event_x}" python3 - <<'PY'
from hashlib import sha256
import os
print(sha256(os.environ["EVENT"].encode()).hexdigest())
PY
)"
digest_y="$(EVENT="${event_y}" python3 - <<'PY'
from hashlib import sha256
import os
print(sha256(os.environ["EVENT"].encode()).hexdigest())
PY
)"

with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v event_x="${event_x}" -v event_y="${event_y}" \
    -v digest_x="${digest_x}" -v digest_y="${digest_y}" <<SQL
SELECT record_audit_outbox_event(
    '${TENANT_ID}'::uuid, '${AUDIT_X}'::uuid, '${OUTBOX_X}'::uuid,
    :'event_x', :'digest_x', 'integration_hub'
);
SELECT record_audit_outbox_event(
    '${TENANT_ID}'::uuid, '${AUDIT_Y}'::uuid, '${OUTBOX_Y}'::uuid,
    :'event_y', :'digest_y', 'integration_hub'
);
SQL

sql_x="BEGIN;
INSERT INTO position_reporting_relationship_version (
    tenant_record_id, position_reporting_relationship_version_id,
    position_reporting_relationship_record_id, manager_position_record_id,
    review_evidence_digest_sha256, application_evidence_digest_sha256,
    reviewer_actor_reference, applied_by_actor_reference, reviewed_at,
    effective_from, audit_event_record_id
) VALUES (
    '${TENANT_ID}', '${VERSION_X}', '${REL_X}', '${POSITION_Y}',
    '${REVIEW_DIGEST_X}', '${digest_x}', '${REVIEWER_X}', '${APPLIER_X}',
    TIMESTAMPTZ '2026-08-24 01:55:00+00', DATE '2026-08-24', '${AUDIT_X}'
);
SELECT pg_sleep(2);
COMMIT;"

sql_y="BEGIN;
INSERT INTO position_reporting_relationship_version (
    tenant_record_id, position_reporting_relationship_version_id,
    position_reporting_relationship_record_id, manager_position_record_id,
    review_evidence_digest_sha256, application_evidence_digest_sha256,
    reviewer_actor_reference, applied_by_actor_reference, reviewed_at,
    effective_from, audit_event_record_id
) VALUES (
    '${TENANT_ID}', '${VERSION_Y}', '${REL_Y}', '${POSITION_X}',
    '${REVIEW_DIGEST_Y}', '${digest_y}', '${REVIEWER_Y}', '${APPLIER_Y}',
    TIMESTAMPTZ '2026-08-24 01:55:00+00', DATE '2026-08-24', '${AUDIT_Y}'
);
COMMIT;"

log_x="$(mktemp)"
log_y="$(mktemp)"
trap 'rm -f "${log_x}" "${log_y}"' EXIT

set +e
(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "${sql_x}" >"${log_x}" 2>&1) &
pid_x=$!
sleep 0.5
with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "${sql_y}" >"${log_y}" 2>&1
status_y=$?
wait "${pid_x}"
status_x=$?
set -e

if [[ ${status_x} -ne 0 ]]; then
    echo "first concurrent position-reporting mutation unexpectedly failed:" >&2
    cat "${log_x}" >&2
    exit 1
fi
if [[ ${status_y} -eq 0 || "$(cat "${log_y}")" != *"cycle"* ]]; then
    echo "concurrent opposite reporting mutations committed a management cycle instead of serializing fail-closed:" >&2
    cat "${log_y}" >&2
    exit 1
fi

committed_count="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM position_reporting_relationship_version
WHERE position_reporting_relationship_version_id IN ('${VERSION_X}'::uuid, '${VERSION_Y}'::uuid);
")"
if [[ "${committed_count}" != "1" ]]; then
    echo "concurrent reporting mutation did not leave exactly one non-cyclic committed edge: ${committed_count}" >&2
    exit 1
fi

echo "position-reporting concurrent cycle prevention passed"
