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

# Direct-DML evidence must describe the exact reviewed bitemporal change, not merely
# point at same-tenant/same-unit rows. These regressions intentionally bypass the
# authoritative function and commit the deferred constraints so immutable evidence
# cannot be forged by a table-capable maintenance path.
UNRELATED_PREDECESSOR_VERSION_ID="30000000-0000-7000-8000-000000000028"
DIRECT_SUCCESSOR_VERSION_ID="30000000-0000-7000-8000-000000000029"
DIRECT_APPLICATION_ID="30000000-0000-7000-8000-000000000033"
DIRECT_AUDIT_ID="30000000-0000-4000-8000-000000000045"
DIRECT_OUTBOX_ID="30000000-0000-4000-8000-000000000046"

with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO organization_unit_version (
    tenant_record_id, organization_unit_version_id, organization_unit_id,
    unit_name, organization_type_code, parent_organization_unit_id,
    effective_from, effective_to
) VALUES (
    '${TENANT_ID}', '${UNRELATED_PREDECESSOR_VERSION_ID}', '${GAP_CHILD_ID}',
    'Historical unrelated child', 'department', NULL,
    DATE '2010-01-01', DATE '2011-01-01'
);
SQL

expect_direct_evidence_failure() {
    local label="$1"
    local needle="$2"
    local predecessor_id="$3"
    local event_source_value="$4"
    local event_type_value="$5"
    local close_current="$6"
    local successor_from="$7"
    local successor_to="$8"
    local successor_name="$9"
    local output status close_sql successor_to_sql

    close_sql=""
    if [[ "${close_current}" == "yes" ]]; then
        close_sql="UPDATE organization_unit_version SET recorded_to = pg_catalog.transaction_timestamp() WHERE tenant_record_id = '${TENANT_ID}'::uuid AND organization_unit_version_id = '${GAP_CHILD_VERSION_ID}'::uuid;"
    fi
    successor_to_sql="NULL"
    if [[ -n "${successor_to}" ]]; then
        successor_to_sql="DATE '${successor_to}'"
    fi

    set +e
    output="$(
        with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
            -v review_json="${gap_review_json}" -v review_digest="${gap_review_sha256}" <<SQL 2>&1
BEGIN;
WITH event AS (
    SELECT pg_catalog.jsonb_build_object(
        'data', pg_catalog.jsonb_build_object(
            'high_impact', true,
            'result_code', 'organization_hierarchy_changed'
        ),
        'datacontenttype', 'application/json',
        'id', '${DIRECT_AUDIT_ID}',
        'orgmetraactor', '${APPLIER}',
        'orgmetraconfirmation', 'human_confirmation:30000000-0000-4000-8000-000000000051',
        'orgmetraevidence', :'review_digest',
        'orgmetrapurpose', 'organization_hierarchy_change_apply',
        'orgmetrareason', 'organizational_realignment',
        'orgmetratenant', '${TENANT_ID}',
        'source', '${event_source_value}',
        'specversion', '1.0',
        'subject', 'organization_unit:${GAP_CHILD_ID}',
        'time', to_char(
            pg_catalog.transaction_timestamp() AT TIME ZONE 'UTC',
            'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'
        ),
        'type', '${event_type_value}'
    )::text AS event_json
), recorded AS (
    SELECT event_json, encode(
        public.digest(pg_catalog.convert_to(event_json, 'UTF8'), 'sha256'),
        'hex'
    ) AS event_digest
    FROM event
)
SELECT public.record_audit_outbox_event(
    '${TENANT_ID}'::uuid,
    '${DIRECT_AUDIT_ID}'::uuid,
    '${DIRECT_OUTBOX_ID}'::uuid,
    event_json,
    event_digest,
    'orgmetra_domain_events'
)
FROM recorded;

INSERT INTO organization_hierarchy_change_application_record (
    tenant_record_id,
    organization_hierarchy_change_application_record_id,
    organization_unit_id,
    predecessor_organization_unit_version_id,
    successor_organization_unit_version_id,
    organization_hierarchy_change_reference,
    current_parent_organization_unit_id,
    proposed_parent_organization_unit_id,
    canonical_review_json,
    review_evidence_digest_sha256,
    organization_unit_snapshot_digest_sha256,
    hierarchy_snapshot_digest_sha256,
    requester_actor_reference,
    reviewer_actor_reference,
    applied_by_actor_reference,
    reason_code,
    effective_on,
    review_packet_recorded_at,
    audit_event_record_id,
    outbox_delivery_record_id
) VALUES (
    '${TENANT_ID}'::uuid,
    '${DIRECT_APPLICATION_ID}'::uuid,
    '${GAP_CHILD_ID}'::uuid,
    '${predecessor_id}'::uuid,
    '${DIRECT_SUCCESSOR_VERSION_ID}'::uuid,
    '30000000-0000-4000-8000-000000000051'::uuid,
    NULL,
    '${GAP_PARENT_ID}'::uuid,
    :'review_json',
    :'review_digest',
    :'review_json'::jsonb ->> 'organization_unit_snapshot_digest',
    :'review_json'::jsonb ->> 'hierarchy_snapshot_digest',
    :'review_json'::jsonb ->> 'requester_reference',
    :'review_json'::jsonb ->> 'reviewer_reference',
    '${APPLIER}',
    'organizational_realignment',
    DATE '${EFFECTIVE_ON}',
    (:'review_json'::jsonb ->> 'recorded_at')::timestamptz,
    '${DIRECT_AUDIT_ID}'::uuid,
    '${DIRECT_OUTBOX_ID}'::uuid
);

${close_sql}

INSERT INTO organization_unit_version (
    tenant_record_id,
    organization_unit_version_id,
    organization_unit_id,
    unit_name,
    organization_type_code,
    parent_organization_unit_id,
    effective_from,
    effective_to,
    recorded_from,
    organization_hierarchy_change_application_record_id
) VALUES (
    '${TENANT_ID}'::uuid,
    '${DIRECT_SUCCESSOR_VERSION_ID}'::uuid,
    '${GAP_CHILD_ID}'::uuid,
    '${successor_name}',
    'department',
    '${GAP_PARENT_ID}'::uuid,
    DATE '${successor_from}',
    ${successor_to_sql},
    pg_catalog.transaction_timestamp(),
    '${DIRECT_APPLICATION_ID}'::uuid
);
COMMIT;
SQL
    )"
    status=$?
    set -e
    if [[ ${status} -eq 0 || "${output}" != *"${needle}"* ]]; then
        echo "${label}: ${output}" >&2
        exit 1
    fi
}

expect_direct_evidence_failure \
    "direct application evidence accepted a same-unit predecessor outside effective_on" \
    "predecessor" \
    "${UNRELATED_PREDECESSOR_VERSION_ID}" \
    "urn:orgmetra:organization_core" \
    "orgmetra.organization.hierarchy_changed" \
    "no" \
    "2011-01-01" \
    "2012-01-01" \
    "Historical forged successor"

expect_direct_evidence_failure \
    "direct application evidence accepted a semantically unrelated successor" \
    "successor" \
    "${GAP_CHILD_VERSION_ID}" \
    "urn:orgmetra:organization_core" \
    "orgmetra.organization.hierarchy_changed" \
    "yes" \
    "2026-09-16" \
    "" \
    "Forged successor"

expect_direct_evidence_failure \
    "direct application evidence accepted a future-effective correction without preserved history" \
    "preserved" \
    "${GAP_CHILD_VERSION_ID}" \
    "urn:orgmetra:organization_core" \
    "orgmetra.organization.hierarchy_changed" \
    "yes" \
    "2026-09-15" \
    "" \
    "Gap child"

expect_direct_evidence_failure \
    "direct application evidence accepted an audit event from the wrong bounded context" \
    "audit event" \
    "${GAP_CHILD_VERSION_ID}" \
    "urn:orgmetra:people_api" \
    "orgmetra.organization.hierarchy_changed" \
    "yes" \
    "2026-09-15" \
    "" \
    "Gap child"

expect_direct_evidence_failure \
    "direct application evidence accepted the wrong audit event family" \
    "audit event" \
    "${GAP_CHILD_VERSION_ID}" \
    "urn:orgmetra:organization_core" \
    "orgmetra.organization.unrelated" \
    "yes" \
    "2026-09-15" \
    "" \
    "Gap child"
