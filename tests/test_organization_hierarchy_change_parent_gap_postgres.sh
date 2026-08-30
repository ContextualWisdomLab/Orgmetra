#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

TENANT_ID="30000000-0000-7000-8000-000000000001"
GAP_CHILD_ID="30000000-0000-7000-8000-000000000011"
GAP_PARENT_ID="30000000-0000-7000-8000-000000000012"
VALID_CHILD_ID="30000000-0000-7000-8000-000000000013"
VALID_PARENT_ID="30000000-0000-7000-8000-000000000014"
GAP_CHILD_VERSION_ID="30000000-0000-7000-8000-000000000021"
GAP_PARENT_FIRST_VERSION_ID="30000000-0000-7000-8000-000000000022"
GAP_PARENT_LATER_VERSION_ID="30000000-0000-7000-8000-000000000023"
VALID_CHILD_VERSION_ID="30000000-0000-7000-8000-000000000024"
VALID_PARENT_VERSION_ID="30000000-0000-7000-8000-000000000025"
GAP_SUCCESSOR_VERSION_ID="30000000-0000-7000-8000-000000000026"
VALID_SUCCESSOR_VERSION_ID="30000000-0000-7000-8000-000000000027"
GAP_APPLICATION_ID="30000000-0000-7000-8000-000000000031"
VALID_APPLICATION_ID="30000000-0000-7000-8000-000000000032"
GAP_AUDIT_ID="30000000-0000-4000-8000-000000000041"
GAP_OUTBOX_ID="30000000-0000-4000-8000-000000000042"
VALID_AUDIT_ID="30000000-0000-4000-8000-000000000043"
VALID_OUTBOX_ID="30000000-0000-4000-8000-000000000044"
REQUESTER="actor:30000000-0000-4000-8000-000000000061"
REVIEWER="actor:30000000-0000-4000-8000-000000000062"
APPLIER="actor:30000000-0000-4000-8000-000000000063"
EFFECTIVE_ON="2026-09-15"

with_tenant() {
    local tenant="$1"
    shift
    PGOPTIONS="-c orgmetra.tenant_record_id=${tenant}" command psql "$@"
}

review_digest() {
    REVIEW_JSON="$1" python3 - <<'PY'
from hashlib import sha256
import os
print(sha256(os.environ["REVIEW_JSON"].encode("utf-8")).hexdigest())
PY
}

build_review() {
    local unit_id="$1"
    local proposed_parent_id="$2"
    local change_reference="$3"
    local unit_digest="$4"
    local hierarchy_digest="$5"
    TENANT_ID="${TENANT_ID}" UNIT_ID="${unit_id}" PROPOSED_PARENT_ID="${proposed_parent_id}" \
    CHANGE_REFERENCE="${change_reference}" REQUESTER="${REQUESTER}" REVIEWER="${REVIEWER}" \
    EFFECTIVE_ON="${EFFECTIVE_ON}" UNIT_DIGEST="${unit_digest}" HIERARCHY_DIGEST="${hierarchy_digest}" \
    PYTHONPATH=packages/organization-hierarchy-change-review/src python3 - <<'PY'
from datetime import date, datetime, timezone
import os
from orgmetra_organization_hierarchy_change_review import build_organization_hierarchy_change_review_packet

packet = build_organization_hierarchy_change_review_packet(
    tenant_record_id=os.environ["TENANT_ID"],
    organization_hierarchy_change_reference=os.environ["CHANGE_REFERENCE"],
    organization_unit_reference=f"organization_unit:{os.environ['UNIT_ID']}",
    current_parent_organization_unit_reference=None,
    proposed_parent_organization_unit_reference=f"organization_unit:{os.environ['PROPOSED_PARENT_ID']}",
    effective_on=date.fromisoformat(os.environ["EFFECTIVE_ON"]),
    organization_unit_snapshot_digest=os.environ["UNIT_DIGEST"],
    hierarchy_snapshot_digest=os.environ["HIERARCHY_DIGEST"],
    requester_reference=os.environ["REQUESTER"],
    reviewer_reference=os.environ["REVIEWER"],
    purpose_code="organization_hierarchy_change_review",
    reason_code="organizational_realignment",
    recorded_at=datetime.now(timezone.utc),
)
print(packet.canonical_json())
PY
}

run_application() {
    local unit_id="$1"
    local predecessor_id="$2"
    local successor_id="$3"
    local application_id="$4"
    local canonical_review_json="$5"
    local digest="$6"
    local audit_id="$7"
    local outbox_id="$8"
    with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
        -v review_json="${canonical_review_json}" -v review_digest="${digest}" <<SQL
SELECT apply_organization_hierarchy_change(
    '${TENANT_ID}'::uuid,
    '${unit_id}'::uuid,
    '${predecessor_id}'::uuid,
    '${successor_id}'::uuid,
    '${application_id}'::uuid,
    :'review_json',
    :'review_digest',
    '${APPLIER}',
    '${audit_id}'::uuid,
    '${outbox_id}'::uuid
);
SQL
}

expect_application_failure() {
    local label="$1"
    local needle="$2"
    shift 2
    local output status
    set +e
    output="$({ run_application "$@"; } 2>&1)"
    status=$?
    set -e
    if [[ ${status} -eq 0 || "${output}" != *"${needle}"* ]]; then
        echo "${label}: ${output}" >&2
        exit 1
    fi
}

with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}', 'tenant_parent_gap_regression');

INSERT INTO organization_unit (tenant_record_id, organization_unit_id)
VALUES
    ('${TENANT_ID}', '${GAP_CHILD_ID}'),
    ('${TENANT_ID}', '${GAP_PARENT_ID}'),
    ('${TENANT_ID}', '${VALID_CHILD_ID}'),
    ('${TENANT_ID}', '${VALID_PARENT_ID}');

INSERT INTO organization_unit_version (
    tenant_record_id, organization_unit_version_id, organization_unit_id,
    unit_name, organization_type_code, parent_organization_unit_id,
    effective_from, effective_to
) VALUES
    ('${TENANT_ID}', '${GAP_CHILD_VERSION_ID}', '${GAP_CHILD_ID}', 'Gap child', 'department', NULL, DATE '2020-01-01', NULL),
    ('${TENANT_ID}', '${GAP_PARENT_FIRST_VERSION_ID}', '${GAP_PARENT_ID}', 'Gap parent first', 'division', NULL, DATE '2020-01-01', DATE '2026-10-01'),
    ('${TENANT_ID}', '${GAP_PARENT_LATER_VERSION_ID}', '${GAP_PARENT_ID}', 'Gap parent later', 'division', NULL, DATE '2026-11-01', NULL),
    ('${TENANT_ID}', '${VALID_CHILD_VERSION_ID}', '${VALID_CHILD_ID}', 'Valid child', 'department', NULL, DATE '2020-01-01', NULL),
    ('${TENANT_ID}', '${VALID_PARENT_VERSION_ID}', '${VALID_PARENT_ID}', 'Valid parent', 'division', NULL, DATE '2020-01-01', NULL);
SQL

gap_unit_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_unit_review_snapshot_digest('${TENANT_ID}'::uuid, '${GAP_CHILD_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
gap_hierarchy_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_hierarchy_review_snapshot_digest('${TENANT_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
gap_review_json="$(build_review "${GAP_CHILD_ID}" "${GAP_PARENT_ID}" "organization_hierarchy_change:30000000-0000-4000-8000-000000000051" "${gap_unit_digest}" "${gap_hierarchy_digest}")"
gap_review_sha256="$(review_digest "${gap_review_json}")"

expect_application_failure \
    "organization hierarchy application accepted a successor whose proposed parent disappears inside the effective interval" \
    "proposed parent is not visible throughout successor effective interval" \
    "${GAP_CHILD_ID}" "${GAP_CHILD_VERSION_ID}" "${GAP_SUCCESSOR_VERSION_ID}" "${GAP_APPLICATION_ID}" \
    "${gap_review_json}" "${gap_review_sha256}" "${GAP_AUDIT_ID}" "${GAP_OUTBOX_ID}"

valid_unit_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_unit_review_snapshot_digest('${TENANT_ID}'::uuid, '${VALID_CHILD_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
valid_hierarchy_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_hierarchy_review_snapshot_digest('${TENANT_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
valid_review_json="$(build_review "${VALID_CHILD_ID}" "${VALID_PARENT_ID}" "organization_hierarchy_change:30000000-0000-4000-8000-000000000052" "${valid_unit_digest}" "${valid_hierarchy_digest}")"
valid_review_sha256="$(review_digest "${valid_review_json}")"
run_application \
    "${VALID_CHILD_ID}" "${VALID_CHILD_VERSION_ID}" "${VALID_SUCCESSOR_VERSION_ID}" "${VALID_APPLICATION_ID}" \
    "${valid_review_json}" "${valid_review_sha256}" "${VALID_AUDIT_ID}" "${VALID_OUTBOX_ID}"

event_source="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "
SELECT canonical_event_json::jsonb ->> 'source'
FROM audit_event_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND audit_event_record_id = '${VALID_AUDIT_ID}'::uuid;")"
if [[ "${event_source}" != "urn:orgmetra:organization_core" ]]; then
    echo "organization hierarchy event attributed the wrong owner: ${event_source}" >&2
    exit 1
fi
