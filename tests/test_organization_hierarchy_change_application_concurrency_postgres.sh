#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

TENANT_ID="31000000-0000-7000-8000-000000000001"
RECOVERY_TENANT_ID="31000000-0000-7000-8000-000000000002"
RECOVERY_X_ID="00000000-0000-7000-8000-000000000201"
RECOVERY_Y_ID="00000000-0000-7000-8000-000000000202"
X_ID="00000000-0000-7000-8000-000000000101"
Y_ID="00000000-0000-7000-8000-000000000102"
X_VERSION_ID="00000000-0000-7000-8000-000000000111"
Y_VERSION_ID="00000000-0000-7000-8000-000000000112"
X_SUCCESSOR_ID="00000000-0000-7000-8000-000000000113"
Y_SUCCESSOR_ID="00000000-0000-7000-8000-000000000114"
REQUESTER="actor:00000000-0000-4000-8000-000000000121"
REVIEWER="actor:00000000-0000-4000-8000-000000000122"
APPLIER="actor:00000000-0000-4000-8000-000000000123"
EFFECTIVE_ON="2026-09-01"

with_tenant() {
    local tenant="$1"
    shift
    PGOPTIONS="-c orgmetra.tenant_record_id=${tenant}" command psql "$@"
}

build_review() {
    local unit_id="$1"
    local proposed_parent="$2"
    local change_reference="$3"
    local unit_digest="$4"
    local hierarchy_digest="$5"
    TENANT_ID="${TENANT_ID}" UNIT_ID="${unit_id}" PROPOSED_PARENT="${proposed_parent}" \
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
    proposed_parent_organization_unit_reference=f"organization_unit:{os.environ['PROPOSED_PARENT']}",
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

digest_review() {
    REVIEW_JSON="$1" python3 - <<'PY'
from hashlib import sha256
import os
print(sha256(os.environ["REVIEW_JSON"].encode("utf-8")).hexdigest())
PY
}

if [[ "$(psql "${DATABASE_URL}" -Atqc "SELECT to_regprocedure('apply_organization_hierarchy_change(uuid,uuid,uuid,uuid,uuid,text,text,text,uuid,uuid)') IS NOT NULL;")" != "t" ]]; then
    echo "authoritative hierarchy application function is missing" >&2
    exit 1
fi

# Reproduce PostgreSQL's documented failed-concurrent-build residue. A failed
# unique concurrent build leaves an INVALID same-named index. Migration 0028
# must be safely retryable from that partial state and must still install its
# stale-transaction function and trigger after repairing all index contracts.
with_tenant "${RECOVERY_TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${RECOVERY_TENANT_ID}', 'tenant_concurrent_index_recovery');
INSERT INTO organization_unit (tenant_record_id, organization_unit_id)
VALUES
    ('${RECOVERY_TENANT_ID}', '${RECOVERY_X_ID}'),
    ('${RECOVERY_TENANT_ID}', '${RECOVERY_Y_ID}');
SQL

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
    "DROP TRIGGER IF EXISTS organization_hierarchy_application_concurrency_guard ON organization_hierarchy_change_application_record;"
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
    "DROP FUNCTION IF EXISTS reject_stale_organization_hierarchy_transaction();"
for index_name in \
    organization_unit_tenant_recorded_from_idx \
    organization_unit_tenant_recorded_to_idx \
    organization_unit_version_tenant_recorded_from_idx \
    organization_unit_version_tenant_recorded_to_idx; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "DROP INDEX CONCURRENTLY IF EXISTS ${index_name};"
done

set +e
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
    "CREATE UNIQUE INDEX CONCURRENTLY organization_unit_tenant_recorded_from_idx ON organization_unit (tenant_record_id);" \
    >/tmp/orgmetra-invalid-index-build.log 2>&1
invalid_build_status=$?
set -e
if [[ ${invalid_build_status} -eq 0 ]]; then
    echo "failed to create the expected invalid concurrent-index residue" >&2
    exit 1
fi
invalid_index_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM pg_class AS index_class
JOIN pg_namespace AS namespace ON namespace.oid = index_class.relnamespace
JOIN pg_index AS index_state ON index_state.indexrelid = index_class.oid
WHERE namespace.nspname = 'public'
  AND index_class.relname = 'organization_unit_tenant_recorded_from_idx'
  AND NOT index_state.indisvalid;")"
if [[ "${invalid_index_count}" != "1" ]]; then
    echo "failed concurrent build did not leave one invalid index residue: ${invalid_index_count}" >&2
    exit 1
fi

set +e
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -f database/migrations/0028_organization_hierarchy_change_concurrency_hardening.sql \
    >/tmp/orgmetra-concurrent-index-recovery.log 2>&1
recovery_status=$?
set -e
if [[ ${recovery_status} -ne 0 ]]; then
    cat /tmp/orgmetra-concurrent-index-recovery.log >&2
    echo "migration 0028 could not recover invalid concurrent-index residue" >&2
    exit 1
fi

invalid_index_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM pg_class AS index_class
JOIN pg_namespace AS namespace ON namespace.oid = index_class.relnamespace
JOIN pg_index AS index_state ON index_state.indexrelid = index_class.oid
WHERE namespace.nspname = 'public'
  AND index_class.relname IN (
      'organization_unit_tenant_recorded_from_idx',
      'organization_unit_tenant_recorded_to_idx',
      'organization_unit_version_tenant_recorded_from_idx',
      'organization_unit_version_tenant_recorded_to_idx'
  )
  AND NOT index_state.indisvalid;")"
if [[ "${invalid_index_count}" != "0" ]]; then
    echo "migration 0028 left invalid hierarchy indexes after recovery: ${invalid_index_count}" >&2
    exit 1
fi
if [[ "$(psql "${DATABASE_URL}" -Atqc "SELECT to_regprocedure('reject_stale_organization_hierarchy_transaction()') IS NOT NULL;")" != "t" ]]; then
    echo "migration 0028 recovery stopped before installing the stale-transaction function" >&2
    exit 1
fi
if [[ "$(psql "${DATABASE_URL}" -Atqc "SELECT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'organization_hierarchy_application_concurrency_guard' AND NOT tgisinternal);")" != "t" ]]; then
    echo "migration 0028 recovery stopped before installing the concurrency trigger" >&2
    exit 1
fi

unhardened_functions="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
  AND proname = 'reject_stale_organization_hierarchy_transaction'
  AND NOT COALESCE(
    proconfig @> ARRAY['search_path=pg_catalog, public, pg_temp']::text[],
    false
  );")"
if [[ "${unhardened_functions}" != "0" ]]; then
    echo "organization hierarchy concurrency guard inherits caller-controlled search_path: ${unhardened_functions}" >&2
    exit 1
fi

stale_guard_index_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM pg_indexes
WHERE schemaname = 'public'
  AND (
    (indexname = 'organization_unit_tenant_recorded_from_idx'
      AND indexdef LIKE '%(tenant_record_id, recorded_from)%')
    OR (indexname = 'organization_unit_tenant_recorded_to_idx'
      AND indexdef LIKE '%(tenant_record_id, recorded_to)%'
      AND indexdef LIKE '%WHERE (recorded_to IS NOT NULL)%')
    OR (indexname = 'organization_unit_version_tenant_recorded_from_idx'
      AND indexdef LIKE '%(tenant_record_id, recorded_from)%')
    OR (indexname = 'organization_unit_version_tenant_recorded_to_idx'
      AND indexdef LIKE '%(tenant_record_id, recorded_to)%'
      AND indexdef LIKE '%WHERE (recorded_to IS NOT NULL)%')
  );")"
if [[ "${stale_guard_index_count}" != "4" ]]; then
    echo "organization hierarchy stale-transaction probes are not fully indexed: ${stale_guard_index_count}/4" >&2
    exit 1
fi

with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}', 'tenant_concurrency');
INSERT INTO organization_unit (tenant_record_id, organization_unit_id)
VALUES ('${TENANT_ID}', '${X_ID}'), ('${TENANT_ID}', '${Y_ID}');
INSERT INTO organization_unit_version (
    tenant_record_id, organization_unit_version_id, organization_unit_id,
    unit_name, organization_type_code, parent_organization_unit_id, effective_from
) VALUES
    ('${TENANT_ID}', '${X_VERSION_ID}', '${X_ID}', 'Unit X', 'division', NULL, DATE '2020-01-01'),
    ('${TENANT_ID}', '${Y_VERSION_ID}', '${Y_ID}', 'Unit Y', 'division', NULL, DATE '2020-01-01');
SQL

x_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_unit_review_snapshot_digest('${TENANT_ID}'::uuid, '${X_ID}'::uuid, DATE '${EFFECTIVE_ON}', clock_timestamp());")"
y_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_unit_review_snapshot_digest('${TENANT_ID}'::uuid, '${Y_ID}'::uuid, DATE '${EFFECTIVE_ON}', clock_timestamp());")"
hierarchy_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_hierarchy_review_snapshot_digest('${TENANT_ID}'::uuid, DATE '${EFFECTIVE_ON}', clock_timestamp());")"

x_review="$(build_review "${X_ID}" "${Y_ID}" "organization_hierarchy_change:00000000-0000-4000-8000-000000000131" "${x_digest}" "${hierarchy_digest}")"
y_review="$(build_review "${Y_ID}" "${X_ID}" "organization_hierarchy_change:00000000-0000-4000-8000-000000000132" "${y_digest}" "${hierarchy_digest}")"
x_review_digest="$(digest_review "${x_review}")"
y_review_digest="$(digest_review "${y_review}")"

old_transaction_output="$(mktemp)"
trap 'rm -f "${old_transaction_output}" /tmp/orgmetra-invalid-index-build.log /tmp/orgmetra-concurrent-index-recovery.log' EXIT

# Start the Y->X transaction first, but delay its mutation. X->Y then commits in
# a later-started transaction. The older transaction must not use its earlier
# transaction timestamp to reconstruct pre-change hierarchy truth and commit a cycle.
(
    with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
        -v review_json="${y_review}" -v review_digest="${y_review_digest}" <<SQL
BEGIN;
SELECT pg_sleep(1.5);
SELECT apply_organization_hierarchy_change(
    '${TENANT_ID}'::uuid,
    '${Y_ID}'::uuid,
    '${Y_VERSION_ID}'::uuid,
    '${Y_SUCCESSOR_ID}'::uuid,
    '00000000-0000-7000-8000-000000000141'::uuid,
    :'review_json', :'review_digest', '${APPLIER}',
    '00000000-0000-4000-8000-000000000142'::uuid,
    '00000000-0000-4000-8000-000000000143'::uuid
);
COMMIT;
SQL
) >"${old_transaction_output}" 2>&1 &
old_pid=$!

sleep 0.35
with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v review_json="${x_review}" -v review_digest="${x_review_digest}" <<SQL
SELECT apply_organization_hierarchy_change(
    '${TENANT_ID}'::uuid,
    '${X_ID}'::uuid,
    '${X_VERSION_ID}'::uuid,
    '${X_SUCCESSOR_ID}'::uuid,
    '00000000-0000-7000-8000-000000000151'::uuid,
    :'review_json', :'review_digest', '${APPLIER}',
    '00000000-0000-4000-8000-000000000152'::uuid,
    '00000000-0000-4000-8000-000000000153'::uuid
);
SQL

set +e
wait "${old_pid}"
old_status=$?
set -e
old_output="$(cat "${old_transaction_output}")"
if [[ ${old_status} -eq 0 ]]; then
    echo "earlier transaction committed after a later hierarchy change: ${old_output}" >&2
    exit 1
fi
if [[ "${old_output}" != *"restart"* && "${old_output}" != *"stale"* && "${old_output}" != *"cycle"* ]]; then
    echo "earlier transaction failed outside the guarded hierarchy boundary: ${old_output}" >&2
    exit 1
fi

cycle_count="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "
WITH RECURSIVE path(start_id, current_id, parent_id, depth) AS (
    SELECT organization_unit_id, organization_unit_id, parent_organization_unit_id, 0
    FROM organization_unit_version
    WHERE tenant_record_id = '${TENANT_ID}'::uuid
      AND recorded_to IS NULL
      AND effective_from <= DATE '${EFFECTIVE_ON}'
      AND (effective_to IS NULL OR DATE '${EFFECTIVE_ON}' < effective_to)
    UNION ALL
    SELECT path.start_id, parent.organization_unit_id, parent.parent_organization_unit_id, path.depth + 1
    FROM path
    JOIN organization_unit_version AS parent
      ON parent.tenant_record_id = '${TENANT_ID}'::uuid
     AND parent.organization_unit_id = path.parent_id
     AND parent.recorded_to IS NULL
     AND parent.effective_from <= DATE '${EFFECTIVE_ON}'
     AND (parent.effective_to IS NULL OR DATE '${EFFECTIVE_ON}' < parent.effective_to)
    WHERE path.parent_id IS NOT NULL AND path.depth < 8
)
SELECT count(*) FROM path WHERE parent_id = start_id;")"
if [[ "${cycle_count}" != "0" ]]; then
    echo "concurrent organization hierarchy changes created a cycle" >&2
    exit 1
fi

echo "organization hierarchy stale-transaction concurrency contract passed"
