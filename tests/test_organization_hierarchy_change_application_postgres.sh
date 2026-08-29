#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0003_audit_outbox_persistence.sql \
    database/migrations/0027_organization_hierarchy_change_application.sql; do
    if [[ ! -f "${migration}" ]]; then
        echo "required organization-hierarchy application migration is missing: ${migration}" >&2
        exit 1
    fi
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

unhardened_functions="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
  AND proname = ANY (ARRAY[
    'organization_unit_review_snapshot_digest',
    'organization_hierarchy_review_snapshot_digest',
    'validate_organization_hierarchy_change_review_evidence',
    'protect_organization_hierarchy_application_history',
    'reject_organization_hierarchy_application_truncate',
    'validate_organization_hierarchy_application_audit',
    'apply_organization_hierarchy_change'
  ])
  AND NOT COALESCE(
    proconfig @> ARRAY['search_path=pg_catalog, public, pg_temp']::text[],
    false
  );")"
if [[ "${unhardened_functions}" != "0" ]]; then
    echo "organization hierarchy functions inherit caller-controlled search_path: ${unhardened_functions}" >&2
    exit 1
fi

TENANT_ID="10000000-0000-7000-8000-000000000001"
OTHER_TENANT_ID="20000000-0000-7000-8000-000000000002"
UNIT_ID="00000000-0000-7000-8000-000000000011"
OLD_PARENT_ID="00000000-0000-7000-8000-000000000012"
NEW_PARENT_ID="00000000-0000-7000-8000-000000000013"
DESCENDANT_ID="00000000-0000-7000-8000-000000000014"
UNIT_VERSION_ID="00000000-0000-7000-8000-000000000021"
OLD_PARENT_VERSION_ID="00000000-0000-7000-8000-000000000022"
NEW_PARENT_VERSION_ID="00000000-0000-7000-8000-000000000023"
DESCENDANT_VERSION_ID="00000000-0000-7000-8000-000000000024"
SUCCESSOR_VERSION_ID="00000000-0000-7000-8000-000000000025"
FUTURE_A_ID="00000000-0000-7000-8000-000000000026"
FUTURE_B_ID="00000000-0000-7000-8000-000000000027"
FUTURE_A_VERSION_ID="00000000-0000-7000-8000-000000000028"
FUTURE_B_VERSION_ID="00000000-0000-7000-8000-000000000029"
FUTURE_A_SUCCESSOR_ID="00000000-0000-7000-8000-00000000002a"
FUTURE_B_SUCCESSOR_ID="00000000-0000-7000-8000-00000000002b"
APPLICATION_ID="00000000-0000-7000-8000-000000000031"
FUTURE_A_APPLICATION_ID="00000000-0000-7000-8000-000000000032"
FUTURE_B_APPLICATION_ID="00000000-0000-7000-8000-000000000033"
AUDIT_ID="00000000-0000-4000-8000-000000000041"
OUTBOX_ID="00000000-0000-4000-8000-000000000042"
FUTURE_A_AUDIT_ID="00000000-0000-4000-8000-000000000043"
FUTURE_A_OUTBOX_ID="00000000-0000-4000-8000-000000000044"
FUTURE_B_AUDIT_ID="00000000-0000-4000-8000-000000000045"
FUTURE_B_OUTBOX_ID="00000000-0000-4000-8000-000000000046"
DIRECT_CROSS_APPLICATION_ID="00000000-0000-7000-8000-000000000034"
DIRECT_MISSING_SUCCESSOR_APPLICATION_ID="00000000-0000-7000-8000-000000000035"
DIRECT_COLUMN_MISMATCH_APPLICATION_ID="00000000-0000-7000-8000-000000000036"
MISSING_SUCCESSOR_VERSION_ID="00000000-0000-7000-8000-00000000002c"
DIRECT_CROSS_AUDIT_ID="00000000-0000-4000-8000-000000000047"
DIRECT_CROSS_OUTBOX_ID="00000000-0000-4000-8000-000000000048"
DIRECT_MISSING_SUCCESSOR_AUDIT_ID="00000000-0000-4000-8000-000000000049"
DIRECT_MISSING_SUCCESSOR_OUTBOX_ID="00000000-0000-4000-8000-00000000004a"
DIRECT_COLUMN_MISMATCH_AUDIT_ID="00000000-0000-4000-8000-00000000004b"
DIRECT_COLUMN_MISMATCH_OUTBOX_ID="00000000-0000-4000-8000-00000000004c"
CHANGE_REFERENCE="organization_hierarchy_change:00000000-0000-4000-8000-000000000051"
REQUESTER="actor:00000000-0000-4000-8000-000000000061"
REVIEWER="actor:00000000-0000-4000-8000-000000000062"
APPLIER="actor:00000000-0000-4000-8000-000000000063"
EFFECTIVE_ON="2026-09-01"

with_tenant() {
    local tenant="$1"
    shift
    PGOPTIONS="-c orgmetra.tenant_record_id=${tenant}" command psql "$@"
}

expect_failure() {
    local label="$1"
    local needle="$2"
    shift 2
    local output status
    set +e
    output="$({ "$@"; } 2>&1)"
    status=$?
    set -e
    if [[ ${status} -eq 0 || "${output}" != *"${needle}"* ]]; then
        echo "${label}: ${output}" >&2
        exit 1
    fi
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
    local current_parent="$2"
    local proposed_parent="$3"
    local change_reference="$4"
    local unit_digest="$5"
    local hierarchy_digest="$6"
    TENANT_ID="${TENANT_ID}" UNIT_ID="${unit_id}" CURRENT_PARENT="${current_parent}" \
    PROPOSED_PARENT="${proposed_parent}" CHANGE_REFERENCE="${change_reference}" \
    REQUESTER="${REQUESTER}" REVIEWER="${REVIEWER}" EFFECTIVE_ON="${EFFECTIVE_ON}" \
    UNIT_DIGEST="${unit_digest}" HIERARCHY_DIGEST="${hierarchy_digest}" \
    PYTHONPATH=packages/organization-hierarchy-change-review/src python3 - <<'PY'
from datetime import date, datetime, timezone
import os
from orgmetra_organization_hierarchy_change_review import build_organization_hierarchy_change_review_packet

def organization_reference(raw: str):
    return None if raw == "ROOT" else f"organization_unit:{raw}"

packet = build_organization_hierarchy_change_review_packet(
    tenant_record_id=os.environ["TENANT_ID"],
    organization_hierarchy_change_reference=os.environ["CHANGE_REFERENCE"],
    organization_unit_reference=f"organization_unit:{os.environ['UNIT_ID']}",
    current_parent_organization_unit_reference=organization_reference(os.environ["CURRENT_PARENT"]),
    proposed_parent_organization_unit_reference=organization_reference(os.environ["PROPOSED_PARENT"]),
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
    local unit_id="$3"
    local predecessor_id="$4"
    local successor_id="$5"
    local application_id="$6"
    local canonical_review_json="$7"
    local digest="$8"
    local audit_id="$9"
    local outbox_id="${10}"
    local output status
    set +e
    output="$(run_application \
        "${unit_id}" "${predecessor_id}" "${successor_id}" "${application_id}" \
        "${canonical_review_json}" "${digest}" "${audit_id}" "${outbox_id}" 2>&1)"
    status=$?
    set -e
    if [[ ${status} -eq 0 || "${output}" != *"${needle}"* ]]; then
        echo "${label}: ${output}" >&2
        exit 1
    fi
}

expect_direct_application_insert_failure() {
    local label="$1"
    local needle="$2"
    local predecessor_id="$3"
    local successor_id="$4"
    local application_id="$5"
    local canonical_review_json="$6"
    local digest="$7"
    local audit_id="$8"
    local outbox_id="$9"
    local current_parent_sql="${10}"
    local proposed_parent_sql="${11}"
    local output status
    set +e
    output="$(
        {
            with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
BEGIN;
WITH event AS (
    SELECT pg_catalog.jsonb_build_object(
        'data', pg_catalog.jsonb_build_object(
            'high_impact', true,
            'result_code', 'organization_hierarchy_changed'
        ),
        'datacontenttype', 'application/json',
        'id', '${audit_id}',
        'orgmetraactor', '${APPLIER}',
        'orgmetraconfirmation', 'human_confirmation:' || replace(
            '${canonical_review_json}'::jsonb ->> 'organization_hierarchy_change_reference',
            'organization_hierarchy_change:',
            ''
        ),
        'orgmetraevidence', '${digest}',
        'orgmetrapurpose', 'organization_hierarchy_change_apply',
        'orgmetrareason', '${canonical_review_json}'::jsonb ->> 'reason_code',
        'orgmetratenant', '${TENANT_ID}',
        'source', 'urn:orgmetra:people_api',
        'specversion', '1.0',
        'subject', 'organization_unit:' || '${FUTURE_B_ID}',
        'time', to_char(
            pg_catalog.transaction_timestamp() AT TIME ZONE 'UTC',
            'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'
        ),
        'type', 'orgmetra.organization.hierarchy_changed'
    )::text AS event_json
), recorded AS (
    SELECT event_json, encode(
        public.digest(pg_catalog.convert_to(event_json, 'UTF8'), 'sha256'), 'hex'
    ) AS event_digest
    FROM event
)
SELECT public.record_audit_outbox_event(
    '${TENANT_ID}'::uuid,
    '${audit_id}'::uuid,
    '${outbox_id}'::uuid,
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
    '${application_id}'::uuid,
    '${FUTURE_B_ID}'::uuid,
    '${predecessor_id}'::uuid,
    '${successor_id}'::uuid,
    substring('${canonical_review_json}'::jsonb ->> 'organization_hierarchy_change_reference' FROM length('organization_hierarchy_change:') + 1)::uuid,
    ${current_parent_sql},
    ${proposed_parent_sql},
    '${canonical_review_json}',
    '${digest}',
    '${canonical_review_json}'::jsonb ->> 'organization_unit_snapshot_digest',
    '${canonical_review_json}'::jsonb ->> 'hierarchy_snapshot_digest',
    '${canonical_review_json}'::jsonb ->> 'requester_reference',
    '${canonical_review_json}'::jsonb ->> 'reviewer_reference',
    '${APPLIER}',
    '${canonical_review_json}'::jsonb ->> 'reason_code',
    ('${canonical_review_json}'::jsonb ->> 'effective_on')::date,
    ('${canonical_review_json}'::jsonb ->> 'recorded_at')::timestamptz,
    '${audit_id}'::uuid,
    '${outbox_id}'::uuid
);
COMMIT;
SQL
        } 2>&1
    )"
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
VALUES
    ('${TENANT_ID}', '${UNIT_ID}'),
    ('${TENANT_ID}', '${OLD_PARENT_ID}'),
    ('${TENANT_ID}', '${NEW_PARENT_ID}'),
    ('${TENANT_ID}', '${DESCENDANT_ID}'),
    ('${TENANT_ID}', '${FUTURE_A_ID}'),
    ('${TENANT_ID}', '${FUTURE_B_ID}');

INSERT INTO organization_unit_version (
    tenant_record_id, organization_unit_version_id, organization_unit_id,
    unit_name, organization_type_code, parent_organization_unit_id, effective_from
) VALUES
    ('${TENANT_ID}', '${OLD_PARENT_VERSION_ID}', '${OLD_PARENT_ID}', 'Old parent', 'division', NULL, DATE '2020-01-01'),
    ('${TENANT_ID}', '${NEW_PARENT_VERSION_ID}', '${NEW_PARENT_ID}', 'New parent', 'division', NULL, DATE '2020-01-01'),
    ('${TENANT_ID}', '${UNIT_VERSION_ID}', '${UNIT_ID}', 'Reviewed unit', 'department', '${OLD_PARENT_ID}', DATE '2020-01-01'),
    ('${TENANT_ID}', '${DESCENDANT_VERSION_ID}', '${DESCENDANT_ID}', 'Descendant', 'team', '${UNIT_ID}', DATE '2020-01-01'),
    ('${TENANT_ID}', '${FUTURE_A_VERSION_ID}', '${FUTURE_A_ID}', 'Future A', 'division', NULL, DATE '2020-01-01'),
    ('${TENANT_ID}', '${FUTURE_B_VERSION_ID}', '${FUTURE_B_ID}', 'Future B', 'division', NULL, DATE '2020-01-01');
SQL

unit_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_unit_review_snapshot_digest('${TENANT_ID}'::uuid, '${UNIT_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
hierarchy_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_hierarchy_review_snapshot_digest('${TENANT_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
if [[ ! "${unit_digest}" =~ ^[0-9a-f]{64}$ || ! "${hierarchy_digest}" =~ ^[0-9a-f]{64}$ ]]; then
    echo "authoritative organization snapshot digests were not produced" >&2
    exit 1
fi

review_json="$(build_review "${UNIT_ID}" "${OLD_PARENT_ID}" "${NEW_PARENT_ID}" "${CHANGE_REFERENCE}" "${unit_digest}" "${hierarchy_digest}")"
review_sha256="$(review_digest "${review_json}")"
run_application \
    "${UNIT_ID}" "${UNIT_VERSION_ID}" "${SUCCESSOR_VERSION_ID}" "${APPLICATION_ID}" \
    "${review_json}" "${review_sha256}" "${AUDIT_ID}" "${OUTBOX_ID}"

current_parent="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "
SELECT COALESCE(parent_organization_unit_id::text, 'ROOT')
FROM organization_unit_version
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND organization_unit_id = '${UNIT_ID}'::uuid
  AND recorded_to IS NULL
  AND effective_from <= DATE '${EFFECTIVE_ON}'
  AND (effective_to IS NULL OR DATE '${EFFECTIVE_ON}' < effective_to);")"
if [[ "${current_parent}" != "${NEW_PARENT_ID}" ]]; then
    echo "organization hierarchy change did not persist reviewed parent: ${current_parent}" >&2
    exit 1
fi

preserved_parent="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "
SELECT COALESCE(parent_organization_unit_id::text, 'ROOT')
FROM organization_unit_version
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND organization_unit_id = '${UNIT_ID}'::uuid
  AND recorded_to IS NULL
  AND effective_from = DATE '2020-01-01'
  AND effective_to = DATE '${EFFECTIVE_ON}';")"
if [[ "${preserved_parent}" != "${OLD_PARENT_ID}" ]]; then
    echo "organization hierarchy application rewrote prior business-time truth: ${preserved_parent}" >&2
    exit 1
fi

application_evidence="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "
SELECT reason_code || '|' || application_state || '|' || decision_authority_state
FROM organization_hierarchy_change_application_record
WHERE organization_hierarchy_change_application_record_id = '${APPLICATION_ID}'::uuid;")"
if [[ "${application_evidence}" != "organizational_realignment|applied_after_human_confirmation|human_review_then_authoritative_application" ]]; then
    echo "organization hierarchy application evidence is incomplete: ${application_evidence}" >&2
    exit 1
fi

null_accept_count="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atq <<SQL
WITH mutated AS (
    SELECT field_name, pg_catalog.jsonb_set('${review_json}'::jsonb, ARRAY[field_name], 'null'::jsonb, false) AS payload
    FROM pg_catalog.unnest(ARRAY[
        'tenant_record_id', 'organization_unit_reference', 'effective_on', 'evidence_version',
        'purpose_code', 'review_state', 'scope_verification_state', 'mutation_state',
        'decision_authority', 'next_action', 'human_review_required', 'contains_person_identifier',
        'contains_worker_value', 'contains_employment_decision', 'organization_unit_snapshot_digest',
        'hierarchy_snapshot_digest', 'organization_hierarchy_change_reference', 'requester_reference',
        'reviewer_reference', 'reason_code', 'recorded_at'
    ]) AS fields(field_name)
)
SELECT count(*)
FROM mutated
WHERE validate_organization_hierarchy_change_review_evidence(
    payload::text,
    encode(public.digest(pg_catalog.convert_to(payload::text, 'UTF8'), 'sha256'), 'hex'),
    '${TENANT_ID}'::uuid,
    '${UNIT_ID}'::uuid,
    '${EFFECTIVE_ON}'::date
) IS NOT FALSE;
SQL
)"
if [[ "${null_accept_count}" != "0" ]]; then
    echo "review validator accepted JSON null fields: ${null_accept_count}" >&2
    exit 1
fi

review_variant_accepts() {
    local field_name="$1"
    local replacement="$2"
    with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atq <<SQL
WITH mutated AS (
    SELECT pg_catalog.jsonb_set(
        '${review_json}'::jsonb,
        '{${field_name}}',
        ${replacement},
        false
    ) AS payload
)
SELECT CASE WHEN validate_organization_hierarchy_change_review_evidence(
    payload::text,
    encode(public.digest(pg_catalog.convert_to(payload::text, 'UTF8'), 'sha256'), 'hex'),
    '${TENANT_ID}'::uuid,
    '${UNIT_ID}'::uuid,
    '${EFFECTIVE_ON}'::date
) IS NOT FALSE THEN 1 ELSE 0 END
FROM mutated;
SQL
}

if [[ "$(review_variant_accepts human_review_required "to_jsonb('true'::text)")" != "0" ]]; then
    echo "review validator accepted a stringified boolean" >&2
    exit 1
fi
if [[ "$(review_variant_accepts evidence_version "to_jsonb('1'::text)")" != "0" ]]; then
    echo "review validator accepted a stringified evidence version" >&2
    exit 1
fi
if [[ "$(review_variant_accepts next_action "'\"release now\"'::jsonb")" != "0" ]]; then
    echo "review validator accepted an arbitrary next action" >&2
    exit 1
fi

# A future-effective edge must be considered when a later review would close the cycle.
EFFECTIVE_ON="2026-10-01"
future_a_unit_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_unit_review_snapshot_digest('${TENANT_ID}'::uuid, '${FUTURE_A_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
future_a_hierarchy_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_hierarchy_review_snapshot_digest('${TENANT_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
future_a_json="$(build_review "${FUTURE_A_ID}" "ROOT" "${FUTURE_B_ID}" "organization_hierarchy_change:00000000-0000-4000-8000-000000000101" "${future_a_unit_digest}" "${future_a_hierarchy_digest}")"
future_a_sha256="$(review_digest "${future_a_json}")"
run_application \
    "${FUTURE_A_ID}" "${FUTURE_A_VERSION_ID}" "${FUTURE_A_SUCCESSOR_ID}" "${FUTURE_A_APPLICATION_ID}" \
    "${future_a_json}" "${future_a_sha256}" "${FUTURE_A_AUDIT_ID}" "${FUTURE_A_OUTBOX_ID}"

EFFECTIVE_ON="2026-09-15"
future_b_unit_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_unit_review_snapshot_digest('${TENANT_ID}'::uuid, '${FUTURE_B_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
future_b_hierarchy_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_hierarchy_review_snapshot_digest('${TENANT_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
future_b_json="$(build_review "${FUTURE_B_ID}" "ROOT" "${FUTURE_A_ID}" "organization_hierarchy_change:00000000-0000-4000-8000-000000000102" "${future_b_unit_digest}" "${future_b_hierarchy_digest}")"
future_b_sha256="$(review_digest "${future_b_json}")"
expect_application_failure \
    "organization hierarchy application accepted a future-effective parent cycle" \
    "cycle" \
    "${FUTURE_B_ID}" "${FUTURE_B_VERSION_ID}" "${FUTURE_B_SUCCESSOR_ID}" "${FUTURE_B_APPLICATION_ID}" \
    "${future_b_json}" "${future_b_sha256}" "${FUTURE_B_AUDIT_ID}" "${FUTURE_B_OUTBOX_ID}"
EFFECTIVE_ON="2026-09-01"

# Direct evidence rows cannot bind a version from another unit or a missing successor.
EFFECTIVE_ON="2026-09-15"
direct_unit_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_unit_review_snapshot_digest('${TENANT_ID}'::uuid, '${FUTURE_B_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
direct_hierarchy_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_hierarchy_review_snapshot_digest('${TENANT_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
direct_cross_json="$(build_review "${FUTURE_B_ID}" "ROOT" "${FUTURE_A_ID}" "organization_hierarchy_change:00000000-0000-4000-8000-000000000111" "${direct_unit_digest}" "${direct_hierarchy_digest}")"
direct_cross_sha256="$(review_digest "${direct_cross_json}")"
expect_direct_application_insert_failure \
    "direct application evidence accepted a cross-unit predecessor" \
    "predecessor" \
    "${NEW_PARENT_VERSION_ID}" "${FUTURE_B_SUCCESSOR_ID}" "${DIRECT_CROSS_APPLICATION_ID}" \
    "${direct_cross_json}" "${direct_cross_sha256}" "${DIRECT_CROSS_AUDIT_ID}" "${DIRECT_CROSS_OUTBOX_ID}" \
    "NULL" "'${FUTURE_A_ID}'::uuid"

direct_column_mismatch_json="$(build_review "${FUTURE_B_ID}" "ROOT" "${FUTURE_A_ID}" "organization_hierarchy_change:00000000-0000-4000-8000-000000000113" "${direct_unit_digest}" "${direct_hierarchy_digest}")"
direct_column_mismatch_sha256="$(review_digest "${direct_column_mismatch_json}")"
expect_direct_application_insert_failure \
    "direct application evidence accepted a mismatched current parent" \
    "columns do not match" \
    "${FUTURE_B_VERSION_ID}" "${MISSING_SUCCESSOR_VERSION_ID}" "${DIRECT_COLUMN_MISMATCH_APPLICATION_ID}" \
    "${direct_column_mismatch_json}" "${direct_column_mismatch_sha256}" \
    "${DIRECT_COLUMN_MISMATCH_AUDIT_ID}" "${DIRECT_COLUMN_MISMATCH_OUTBOX_ID}" \
    "'${OLD_PARENT_ID}'::uuid" "'${FUTURE_A_ID}'::uuid"

direct_missing_successor_json="$(build_review "${FUTURE_B_ID}" "ROOT" "${FUTURE_A_ID}" "organization_hierarchy_change:00000000-0000-4000-8000-000000000112" "${direct_unit_digest}" "${direct_hierarchy_digest}")"
direct_missing_successor_sha256="$(review_digest "${direct_missing_successor_json}")"
expect_direct_application_insert_failure \
    "direct application evidence accepted a missing successor" \
    "successor" \
    "${FUTURE_B_VERSION_ID}" "${MISSING_SUCCESSOR_VERSION_ID}" "${DIRECT_MISSING_SUCCESSOR_APPLICATION_ID}" \
    "${direct_missing_successor_json}" "${direct_missing_successor_sha256}" \
    "${DIRECT_MISSING_SUCCESSOR_AUDIT_ID}" "${DIRECT_MISSING_SUCCESSOR_OUTBOX_ID}" \
    "NULL" "'${FUTURE_A_ID}'::uuid"
EFFECTIVE_ON="2026-09-01"

expect_failure \
    "organization hierarchy application evidence was rewriteable" \
    "append-only" \
    with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
    "UPDATE organization_hierarchy_change_application_record SET reason_code = 'administrative_correction' WHERE organization_hierarchy_change_application_record_id = '${APPLICATION_ID}'::uuid;"

expect_failure \
    "organization hierarchy application evidence could be truncated" \
    "cannot be truncated" \
    with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
    "TRUNCATE organization_hierarchy_change_application_record CASCADE;"

# Fresh evidence that lies about the current parent must be rejected before mutation.
stale_unit_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_unit_review_snapshot_digest('${TENANT_ID}'::uuid, '${UNIT_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
stale_hierarchy_digest="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "SELECT organization_hierarchy_review_snapshot_digest('${TENANT_ID}'::uuid, DATE '${EFFECTIVE_ON}', pg_catalog.transaction_timestamp());")"
stale_json="$(build_review "${UNIT_ID}" "${OLD_PARENT_ID}" "${DESCENDANT_ID}" "organization_hierarchy_change:00000000-0000-4000-8000-000000000071" "${stale_unit_digest}" "${stale_hierarchy_digest}")"
stale_sha256="$(review_digest "${stale_json}")"
expect_application_failure \
    "organization hierarchy application accepted stale current-parent evidence" \
    "stale" \
    "${UNIT_ID}" "${SUCCESSOR_VERSION_ID}" \
    "00000000-0000-7000-8000-000000000075" \
    "00000000-0000-7000-8000-000000000076" \
    "${stale_json}" "${stale_sha256}" \
    "00000000-0000-4000-8000-000000000077" \
    "00000000-0000-4000-8000-000000000078"

# A proposed parent that is currently a descendant would form a cycle.
cycle_json="$(build_review "${UNIT_ID}" "${NEW_PARENT_ID}" "${DESCENDANT_ID}" "organization_hierarchy_change:00000000-0000-4000-8000-000000000081" "${stale_unit_digest}" "${stale_hierarchy_digest}")"
cycle_sha256="$(review_digest "${cycle_json}")"
expect_application_failure \
    "organization hierarchy application accepted a parent cycle" \
    "cycle" \
    "${UNIT_ID}" "${SUCCESSOR_VERSION_ID}" \
    "00000000-0000-7000-8000-000000000085" \
    "00000000-0000-7000-8000-000000000086" \
    "${cycle_json}" "${cycle_sha256}" \
    "00000000-0000-4000-8000-000000000087" \
    "00000000-0000-4000-8000-000000000088"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'orgmetra_hierarchy_reader') THEN
        CREATE ROLE orgmetra_hierarchy_reader LOGIN PASSWORD 'orgmetra_hierarchy_reader' NOSUPERUSER NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'orgmetra_untrusted_executor') THEN
        CREATE ROLE orgmetra_untrusted_executor LOGIN PASSWORD 'orgmetra_untrusted_executor' NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;
GRANT CONNECT ON DATABASE orgmetra TO orgmetra_hierarchy_reader, orgmetra_untrusted_executor;
GRANT USAGE ON SCHEMA public TO orgmetra_hierarchy_reader, orgmetra_untrusted_executor;
GRANT SELECT ON organization_hierarchy_change_application_record TO orgmetra_hierarchy_reader;
SQL

alpha_count="$(PGPASSWORD=orgmetra_hierarchy_reader PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" psql -h localhost -U orgmetra_hierarchy_reader -d orgmetra -Atqc 'SELECT count(*) FROM organization_hierarchy_change_application_record;')"
beta_count="$(PGPASSWORD=orgmetra_hierarchy_reader PGOPTIONS="-c orgmetra.tenant_record_id=${OTHER_TENANT_ID}" psql -h localhost -U orgmetra_hierarchy_reader -d orgmetra -Atqc 'SELECT count(*) FROM organization_hierarchy_change_application_record;')"
missing_count="$(PGPASSWORD=orgmetra_hierarchy_reader psql -h localhost -U orgmetra_hierarchy_reader -d orgmetra -Atqc 'SELECT count(*) FROM organization_hierarchy_change_application_record;')"
if [[ "${alpha_count}" != "2" || "${beta_count}" != "0" || "${missing_count}" != "0" ]]; then
    echo "organization hierarchy application RLS isolation failed: alpha=${alpha_count} beta=${beta_count} missing=${missing_count}" >&2
    exit 1
fi

expect_failure \
    "PUBLIC-like runtime role could execute authoritative hierarchy mutation" \
    "permission denied for function apply_organization_hierarchy_change" \
    env PGPASSWORD=orgmetra_untrusted_executor PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
    psql -h localhost -U orgmetra_untrusted_executor -d orgmetra -v ON_ERROR_STOP=1 -c \
    "SELECT apply_organization_hierarchy_change('${TENANT_ID}'::uuid, '${UNIT_ID}'::uuid, '${SUCCESSOR_VERSION_ID}'::uuid, '00000000-0000-7000-8000-000000000091'::uuid, '00000000-0000-7000-8000-000000000092'::uuid, '{}'::text, repeat('a',64), '${APPLIER}', '00000000-0000-4000-8000-000000000093'::uuid, '00000000-0000-4000-8000-000000000094'::uuid);"

echo "organization hierarchy change application contract passed"
