#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
ROOT_URL="${DATABASE_URL%/*}"
RETRO_DB="orgmetra_capacity_retro"
RETRO_URL="${ROOT_URL}/${RETRO_DB}"

psql "${ROOT_URL}/postgres" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ${RETRO_DB};"
psql "${ROOT_URL}/postgres" -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${RETRO_DB};"
trap 'psql "${ROOT_URL}/postgres" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS '${RETRO_DB}' WITH (FORCE);" >/dev/null 2>&1 || true' EXIT

for migration in \
  database/migrations/0001_foundation_schema.sql \
  database/migrations/0002_sealed_evidence_digest.sql \
  database/migrations/0031_employment_work_capacity_persistence.sql \
  database/migrations/0032_employment_work_capacity_forward_chain.sql; do
  psql "${RETRO_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT="30000000-0000-7000-8000-000000000001"
PERSON="30000000-0000-7000-8000-000000000011"
EMPLOYMENT="30000000-0000-7000-8000-000000000021"
EMPLOYMENT_VERSION="30000000-0000-7000-8000-000000000022"
CAPACITY_RECORD="30000000-0000-7000-8000-000000000031"
REQUESTER="actor:00000000-0000-4000-8000-000000000071"
REVIEWER="actor:00000000-0000-4000-8000-000000000072"
APPLIER="actor:00000000-0000-4000-8000-000000000073"
TERMS="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
POLICY="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
REVIEWER_DIGEST="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
AUDIT_DIGEST="dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
NEXT_ACTION="Within tenant_record_id, re-resolve the authoritative Employment and current work-capacity truth at effective_on, verify reviewer identity/authority and the exact reviewed employment-terms and capacity-policy evidence, recalculate Assignment allocation and compensation/payroll impacts, then persist any approved bitemporal capacity change with immutable audit/outbox evidence. This packet does not itself mutate Employment, Assignment, compensation, payroll, leave, or scheduling."

with_tenant() {
  PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT}" command psql "$@"
}

make_review() {
  local current="$1"
  local proposed="$2"
  local effective="$3"
  local recorded="$4"
  python - "$current" "$proposed" "$effective" "$recorded" <<PY
import hashlib, json, sys
current, proposed, effective, recorded = sys.argv[1:]
payload = {
    "capacity_policy_evidence_digest": "${POLICY}",
    "current_capacity_ratio": current,
    "decision_authority": "not_authorized_to_change_employment_or_compensation",
    "effective_on": effective,
    "employment_record_reference": "employment_record:${EMPLOYMENT}",
    "employment_terms_evidence_digest": "${TERMS}",
    "evidence_version": 1,
    "human_review_required": True,
    "next_action": "${NEXT_ACTION}",
    "proposed_capacity_ratio": proposed,
    "purpose_code": "employment_work_capacity_review",
    "reason_code": "employee_agreed_change",
    "recorded_at": recorded,
    "requester_actor_reference": "${REQUESTER}",
    "review_state": "reviewed_for_authoritative_resolution",
    "reviewed_at": "2026-08-26T10:00:00Z",
    "reviewer_actor_reference": "${REVIEWER}",
    "reviewer_identity_evidence_digest": "${REVIEWER_DIGEST}",
    "tenant_record_id": "${TENANT}",
}
raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
print(raw.replace("'", "''"))
print(hashlib.sha256(raw.encode("utf-8")).hexdigest())
PY
}

readarray -t REVIEW1 < <(make_review "0.8000" "1.0000" "2026-09-01" "2026-08-26T10:00:01Z")
readarray -t REVIEW2 < <(make_review "1.0000" "0.6000" "2026-10-01" "2026-08-26T10:00:02Z")
readarray -t RETRO < <(make_review "1.0000" "0.9000" "2026-09-15" "2026-08-26T10:00:03Z")

with_tenant "${RETRO_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT}', 'tenant_retro');
INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES ('${TENANT}', '${PERSON}');
INSERT INTO employment_record (tenant_record_id, employment_record_id, person_record_id)
VALUES ('${TENANT}', '${EMPLOYMENT}', '${PERSON}');
INSERT INTO employment_record_version (
  tenant_record_id, employment_record_version_id, employment_record_id,
  employment_status_code, effective_from, effective_to
) VALUES (
  '${TENANT}', '${EMPLOYMENT_VERSION}', '${EMPLOYMENT}',
  'active', DATE '2026-01-01', DATE '2027-01-01'
);

SELECT apply_employment_work_capacity_change(
  '${TENANT}'::uuid, '${CAPACITY_RECORD}'::uuid,
  '30000000-0000-7000-8000-000000000032'::uuid, '${EMPLOYMENT}'::uuid,
  '${REVIEW1[0]}', '${REVIEW1[1]}',
  'audit_event:00000000-0000-4000-8000-000000000081', '${AUDIT_DIGEST}', '${APPLIER}',
  'audit_event:00000000-0000-4000-8000-000000000082',
  'outbox_event:00000000-0000-4000-8000-000000000083',
  'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
);

SELECT apply_employment_work_capacity_change(
  '${TENANT}'::uuid, '${CAPACITY_RECORD}'::uuid,
  '30000000-0000-7000-8000-000000000033'::uuid, '${EMPLOYMENT}'::uuid,
  '${REVIEW2[0]}', '${REVIEW2[1]}',
  'audit_event:00000000-0000-4000-8000-000000000084', '${AUDIT_DIGEST}', '${APPLIER}',
  'audit_event:00000000-0000-4000-8000-000000000085',
  'outbox_event:00000000-0000-4000-8000-000000000086',
  'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'
);
SQL

set +e
output="$(with_tenant "${RETRO_URL}" -v ON_ERROR_STOP=1 <<SQL 2>&1
SELECT apply_employment_work_capacity_change(
  '${TENANT}'::uuid, '${CAPACITY_RECORD}'::uuid,
  '30000000-0000-7000-8000-000000000034'::uuid, '${EMPLOYMENT}'::uuid,
  '${RETRO[0]}', '${RETRO[1]}',
  'audit_event:00000000-0000-4000-8000-000000000087', '${AUDIT_DIGEST}', '${APPLIER}',
  'audit_event:00000000-0000-4000-8000-000000000088',
  'outbox_event:00000000-0000-4000-8000-000000000089',
  '1111111111111111111111111111111111111111111111111111111111111111'
);
SQL
)"
status=$?
set -e

if [[ ${status} -eq 0 || "${output}" != *"retroactive capacity changes require a dedicated correction/replay boundary"* ]]; then
  echo "retroactive capacity application was not fail-closed: ${output}" >&2
  exit 1
fi

resolved_oct="$(with_tenant "${RETRO_URL}" -Atqc "
SELECT resolve_employment_work_capacity(
  '${TENANT}'::uuid, '${EMPLOYMENT}'::uuid, DATE '2026-10-01', pg_catalog.transaction_timestamp()
)::text;")"
if [[ "${resolved_oct}" != "0.6000" ]]; then
  echo "failed retroactive attempt changed authoritative October capacity: ${resolved_oct}" >&2
  exit 1
fi

printf '%s\n' "Employment work-capacity retroactive-chain protection: PASS"
