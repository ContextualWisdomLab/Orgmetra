#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
ROOT_URL="${DATABASE_URL%/*}"
CANONICAL_DB="orgmetra_capacity_canonical"
CANONICAL_URL="${ROOT_URL}/${CANONICAL_DB}"

psql "${ROOT_URL}/postgres" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ${CANONICAL_DB};"
psql "${ROOT_URL}/postgres" -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${CANONICAL_DB};"
trap 'psql "${ROOT_URL}/postgres" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS '${CANONICAL_DB}' WITH (FORCE);" >/dev/null 2>&1 || true' EXIT

migrations=(
  database/migrations/0001_foundation_schema.sql
  database/migrations/0002_sealed_evidence_digest.sql
  database/migrations/0031_employment_work_capacity_persistence.sql
  database/migrations/0032_employment_work_capacity_forward_chain.sql
)
if [[ -f database/migrations/0033_employment_work_capacity_canonical_evidence.sql ]]; then
  migrations+=(database/migrations/0033_employment_work_capacity_canonical_evidence.sql)
fi
for migration in "${migrations[@]}"; do
  psql "${CANONICAL_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

unhardened_functions="$(psql "${CANONICAL_URL}" -Atqc "
SELECT count(*)
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
  AND proname = 'enforce_employment_work_capacity_canonical_review_evidence'
  AND NOT COALESCE(
    proconfig @> ARRAY['search_path=pg_catalog, public, pg_temp']::text[],
    false
  );")"
if [[ "${unhardened_functions}" != "0" ]]; then
  echo "canonical work-capacity evidence trigger inherits caller-controlled search_path: ${unhardened_functions}" >&2
  exit 1
fi

TENANT_ID="40000000-0000-7000-8000-000000000001"
PERSON_ID="40000000-0000-7000-8000-000000000011"
EMPLOYMENT_ID="40000000-0000-7000-8000-000000000021"
EMPLOYMENT_VERSION_ID="40000000-0000-7000-8000-000000000022"
CAPACITY_RECORD_ID="40000000-0000-7000-8000-000000000031"
CAPACITY_VERSION_ID="40000000-0000-7000-8000-000000000032"
REQUESTER="actor:00000000-0000-4000-8000-000000000041"
REVIEWER="actor:00000000-0000-4000-8000-000000000042"
APPLIER="actor:00000000-0000-4000-8000-000000000043"
TERMS_DIGEST="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
POLICY_DIGEST="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
REVIEWER_DIGEST="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
REVIEW_AUDIT="audit_event:00000000-0000-4000-8000-000000000051"
REVIEW_AUDIT_DIGEST="dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
APPLICATION_AUDIT="audit_event:00000000-0000-4000-8000-000000000052"
APPLICATION_OUTBOX="outbox_event:00000000-0000-4000-8000-000000000061"
APPLICATION_DIGEST="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"

with_tenant() {
  PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

with_tenant "${CANONICAL_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}', 'tenant_canonical');
INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES ('${TENANT_ID}', '${PERSON_ID}');
INSERT INTO employment_record (tenant_record_id, employment_record_id, person_record_id)
VALUES ('${TENANT_ID}', '${EMPLOYMENT_ID}', '${PERSON_ID}');
INSERT INTO employment_record_version (
  tenant_record_id, employment_record_version_id, employment_record_id,
  employment_status_code, effective_from, effective_to
) VALUES (
  '${TENANT_ID}', '${EMPLOYMENT_VERSION_ID}', '${EMPLOYMENT_ID}',
  'active', DATE '2026-01-01', DATE '2027-01-01'
);
SQL

# This payload is semantically identical to a valid parent #103 packet, but its
# whitespace/key order are deliberately noncanonical. Re-hashing alternate bytes
# must not let a caller manufacture a second durable evidence representation.
eval "$(python - <<PY
import hashlib, json, shlex
payload = {
    "tenant_record_id": "${TENANT_ID}",
    "reviewer_identity_evidence_digest": "${REVIEWER_DIGEST}",
    "reviewer_actor_reference": "${REVIEWER}",
    "reviewed_at": "2026-08-26T10:00:00Z",
    "review_state": "reviewed_for_authoritative_resolution",
    "requester_actor_reference": "${REQUESTER}",
    "recorded_at": "2026-08-26T10:00:01Z",
    "reason_code": "employee_agreed_change",
    "purpose_code": "employment_work_capacity_review",
    "proposed_capacity_ratio": "1.0000",
    "next_action": "Within tenant_record_id, re-resolve the authoritative Employment and current work-capacity truth at effective_on, verify reviewer identity/authority and the exact reviewed employment-terms and capacity-policy evidence, recalculate Assignment allocation and compensation/payroll impacts, then persist any approved bitemporal capacity change with immutable audit/outbox evidence. This packet does not itself mutate Employment, Assignment, compensation, payroll, leave, or scheduling.",
    "human_review_required": True,
    "evidence_version": 1,
    "employment_terms_evidence_digest": "${TERMS_DIGEST}",
    "employment_record_reference": "employment_record:${EMPLOYMENT_ID}",
    "effective_on": "2026-09-01",
    "decision_authority": "not_authorized_to_change_employment_or_compensation",
    "current_capacity_ratio": "0.8000",
    "capacity_policy_evidence_digest": "${POLICY_DIGEST}",
}
raw = json.dumps(payload, sort_keys=False, separators=(", ", ": "), ensure_ascii=True)
print("NONCANONICAL_JSON_SQL=" + shlex.quote(raw.replace(chr(39), chr(39) * 2)))
print("NONCANONICAL_DIGEST=" + hashlib.sha256(raw.encode("utf-8")).hexdigest())
PY
)"

set +e
output="$(with_tenant "${CANONICAL_URL}" -v ON_ERROR_STOP=1 -c "
SELECT apply_employment_work_capacity_change(
  '${TENANT_ID}'::uuid,
  '${CAPACITY_RECORD_ID}'::uuid,
  '${CAPACITY_VERSION_ID}'::uuid,
  '${EMPLOYMENT_ID}'::uuid,
  '${NONCANONICAL_JSON_SQL}',
  '${NONCANONICAL_DIGEST}',
  '${REVIEW_AUDIT}',
  '${REVIEW_AUDIT_DIGEST}',
  '${APPLIER}',
  '${APPLICATION_AUDIT}',
  '${APPLICATION_OUTBOX}',
  '${APPLICATION_DIGEST}'
);" 2>&1)"
status=$?
set -e

if [[ ${status} -eq 0 ]]; then
  echo "noncanonical review evidence was accepted after caller recomputed its digest" >&2
  exit 1
fi
if [[ "${output}" != *"review evidence must use exact canonical JSON bytes"* ]]; then
  echo "noncanonical review evidence failed at the wrong boundary: ${output}" >&2
  exit 1
fi

anchor_count="$(with_tenant "${CANONICAL_URL}" -Atqc "
SELECT count(*) FROM employment_work_capacity_record
WHERE employment_record_id='${EMPLOYMENT_ID}'::uuid;")"
if [[ "${anchor_count}" != "0" ]]; then
  echo "failed noncanonical application left an orphan work-capacity anchor" >&2
  exit 1
fi

echo "employment work-capacity canonical evidence regression passed"
