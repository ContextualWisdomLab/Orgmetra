#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

TENANT_ID="32000000-0000-7000-8000-000000000001"
CHILD_ID="32000000-0000-7000-8000-000000000011"
PARENT_ID="32000000-0000-7000-8000-000000000012"
PREDECESSOR_ID="32000000-0000-7000-8000-000000000021"
PARENT_VERSION_ID="32000000-0000-7000-8000-000000000022"
SUCCESSOR_ID="32000000-0000-7000-8000-000000000023"
SPURIOUS_PRESERVED_ID="32000000-0000-7000-8000-000000000024"
APPLICATION_ID="32000000-0000-7000-8000-000000000031"
AUDIT_ID="32000000-0000-4000-8000-000000000041"
OUTBOX_ID="32000000-0000-4000-8000-000000000042"
CHANGE_ID="32000000-0000-4000-8000-000000000051"
REQUESTER="actor:32000000-0000-4000-8000-000000000061"
REVIEWER="actor:32000000-0000-4000-8000-000000000062"
APPLIER="actor:32000000-0000-4000-8000-000000000063"
EFFECTIVE_ON="2026-09-15"

with_tenant() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

with_tenant "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}', 'tenant_unexpected_preserved_segment');
INSERT INTO organization_unit (tenant_record_id, organization_unit_id)
VALUES
    ('${TENANT_ID}', '${CHILD_ID}'),
    ('${TENANT_ID}', '${PARENT_ID}');
INSERT INTO organization_unit_version (
    tenant_record_id, organization_unit_version_id, organization_unit_id,
    unit_name, organization_type_code, parent_organization_unit_id,
    effective_from, effective_to
) VALUES
    ('${TENANT_ID}', '${PREDECESSOR_ID}', '${CHILD_ID}', 'No split child', 'department', NULL, DATE '${EFFECTIVE_ON}', NULL),
    ('${TENANT_ID}', '${PARENT_VERSION_ID}', '${PARENT_ID}', 'No split parent', 'division', NULL, DATE '2020-01-01', NULL);
SQL

unit_digest="$(with_tenant "${DATABASE_URL}" -Atqc "SELECT organization_unit_review_snapshot_digest('${TENANT_ID}'::uuid, '${CHILD_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
hierarchy_digest="$(with_tenant "${DATABASE_URL}" -Atqc "SELECT organization_hierarchy_review_snapshot_digest('${TENANT_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"

review_json="$(
    TENANT_ID="${TENANT_ID}" CHILD_ID="${CHILD_ID}" PARENT_ID="${PARENT_ID}" CHANGE_ID="${CHANGE_ID}" \
    REQUESTER="${REQUESTER}" REVIEWER="${REVIEWER}" EFFECTIVE_ON="${EFFECTIVE_ON}" \
    UNIT_DIGEST="${unit_digest}" HIERARCHY_DIGEST="${hierarchy_digest}" \
    PYTHONPATH=packages/organization-hierarchy-change-review/src python3 - <<'PY'
from datetime import date, datetime, timezone
import os
from orgmetra_organization_hierarchy_change_review import build_organization_hierarchy_change_review_packet

packet = build_organization_hierarchy_change_review_packet(
    tenant_record_id=os.environ["TENANT_ID"],
    organization_hierarchy_change_reference=f"organization_hierarchy_change:{os.environ['CHANGE_ID']}",
    organization_unit_reference=f"organization_unit:{os.environ['CHILD_ID']}",
    current_parent_organization_unit_reference=None,
    proposed_parent_organization_unit_reference=f"organization_unit:{os.environ['PARENT_ID']}",
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
)"
review_digest="$(REVIEW_JSON="${review_json}" python3 - <<'PY'
from hashlib import sha256
import os
print(sha256(os.environ["REVIEW_JSON"].encode("utf-8")).hexdigest())
PY
)"

set +e
output="$(
    with_tenant "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
        -v review_json="${review_json}" -v review_digest="${review_digest}" <<SQL 2>&1
BEGIN;
WITH event AS (
    SELECT pg_catalog.jsonb_build_object(
        'data', pg_catalog.jsonb_build_object(
            'high_impact', true,
            'result_code', 'organization_hierarchy_changed'
        ),
        'datacontenttype', 'application/json',
        'id', '${AUDIT_ID}',
        'orgmetraactor', '${APPLIER}',
        'orgmetraconfirmation', 'human_confirmation:${CHANGE_ID}',
        'orgmetraevidence', :'review_digest',
        'orgmetrapurpose', 'organization_hierarchy_change_apply',
        'orgmetrareason', 'organizational_realignment',
        'orgmetratenant', '${TENANT_ID}',
        'source', 'urn:orgmetra:organization_core',
        'specversion', '1.0',
        'subject', 'organization_unit:${CHILD_ID}',
        'time', to_char(
            pg_catalog.transaction_timestamp() AT TIME ZONE 'UTC',
            'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'
        ),
        'type', 'orgmetra.organization.hierarchy_changed'
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
    '${AUDIT_ID}'::uuid,
    '${OUTBOX_ID}'::uuid,
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
    '${APPLICATION_ID}'::uuid,
    '${CHILD_ID}'::uuid,
    '${PREDECESSOR_ID}'::uuid,
    '${SUCCESSOR_ID}'::uuid,
    '${CHANGE_ID}'::uuid,
    NULL,
    '${PARENT_ID}'::uuid,
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
    '${AUDIT_ID}'::uuid,
    '${OUTBOX_ID}'::uuid
);

UPDATE organization_unit_version
SET recorded_to = pg_catalog.transaction_timestamp()
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND organization_unit_version_id = '${PREDECESSOR_ID}'::uuid;

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
) VALUES
    (
        '${TENANT_ID}'::uuid,
        '${SPURIOUS_PRESERVED_ID}'::uuid,
        '${CHILD_ID}'::uuid,
        'No split child',
        'department',
        NULL,
        DATE '2020-01-01',
        DATE '${EFFECTIVE_ON}',
        pg_catalog.transaction_timestamp(),
        '${APPLICATION_ID}'::uuid
    ),
    (
        '${TENANT_ID}'::uuid,
        '${SUCCESSOR_ID}'::uuid,
        '${CHILD_ID}'::uuid,
        'No split child',
        'department',
        '${PARENT_ID}'::uuid,
        DATE '${EFFECTIVE_ON}',
        NULL,
        pg_catalog.transaction_timestamp(),
        '${APPLICATION_ID}'::uuid
    );
COMMIT;
SQL
)"
status=$?
set -e

if [[ ${status} -eq 0 || "${output}" != *"unexpected preserved"* ]]; then
    echo "direct application evidence accepted an unexpected preserved segment when no split was required: ${output}" >&2
    exit 1
fi

echo "organization hierarchy no-split preservation contract passed"
