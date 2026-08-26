#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
  database/migrations/0001_foundation_schema.sql \
  database/migrations/0002_sealed_evidence_digest.sql \
  database/migrations/0003_audit_outbox_persistence.sql \
  database/migrations/0029_performance_goal_plan_persistence.sql; do
  [[ -f "${migration}" ]] || { echo "required performance-goal persistence migration is missing: ${migration}" >&2; exit 1; }
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="10000000-0000-7000-8000-000000000001"
OTHER_TENANT_ID="20000000-0000-7000-8000-000000000002"
PERSON_ID="10000000-0000-7000-8000-000000000011"
EMPLOYMENT_ID="10000000-0000-7000-8000-000000000021"
JOB_ID="10000000-0000-7000-8000-000000000031"
PLAN_RECORD_ID="10000000-0000-7000-8000-000000000041"
PLAN_VERSION_ID="10000000-0000-7000-8000-000000000042"
PLAN_REFERENCE="performance_goal_plan:00000000-0000-4000-8000-000000000043"
CYCLE_REFERENCE="performance_cycle:10000000-0000-7000-8000-000000000044"
ACTIVATION_REFERENCE="performance_goal_activation:00000000-0000-4000-8000-000000000045"
ACTOR_REFERENCE="actor:00000000-0000-4000-8000-000000000046"
AUTHORITY_REFERENCE="performance_goal_authority:00000000-0000-4000-8000-000000000047"
AUDIT_ID="10000000-0000-7000-8000-000000000051"
OUTBOX_ID="10000000-0000-7000-8000-000000000052"
GOAL_DIGEST="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
MEASUREMENT_DIGEST="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
PLAN_DIGEST="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
ACTIVATION_DIGEST="dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
AUTHORITY_DIGEST="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
APPROVED_AT="2026-08-26T00:00:00Z"
ACTIVATED_AT="2026-08-26T00:01:00Z"

with_tenant() {
  local tenant="$1"; shift
  PGOPTIONS="-c orgmetra.tenant_record_id=${tenant}" command psql "$@"
}

expect_failure() {
  local label="$1" needle="$2" sql="$3" output status
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
INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES ('${TENANT_ID}', '${PERSON_ID}');
INSERT INTO employment_record (tenant_record_id, employment_record_id, person_record_id)
VALUES ('${TENANT_ID}', '${EMPLOYMENT_ID}', '${PERSON_ID}');
INSERT INTO employment_record_version (
  tenant_record_id, employment_record_version_id, employment_record_id,
  employment_status_code, effective_from, effective_to
) VALUES
  ('${TENANT_ID}', '10000000-0000-7000-8000-000000000022', '${EMPLOYMENT_ID}', 'active', DATE '2026-01-01', DATE '2027-01-01'),
  ('${TENANT_ID}', '10000000-0000-7000-8000-000000000023', '${EMPLOYMENT_ID}', 'active', DATE '2027-01-01', DATE '2028-01-01');
INSERT INTO job_profile (tenant_record_id, job_profile_id)
VALUES ('${TENANT_ID}', '${JOB_ID}');
INSERT INTO job_profile_version (
  tenant_record_id, job_profile_version_id, job_profile_id,
  job_title, job_family_code, job_version_code, effective_from, effective_to
) VALUES (
  '${TENANT_ID}', '10000000-0000-7000-8000-000000000032', '${JOB_ID}',
  'Platform Engineer', 'engineering', 'v1', DATE '2026-01-01', DATE '2027-01-01'
);

WITH event_payload AS (
  SELECT jsonb_build_object(
    'specversion','1.0', 'id','${AUDIT_ID}', 'source','urn:orgmetra:performance_goal',
    'type','orgmetra.performance_goal.plan_persisted', 'subject','${PLAN_REFERENCE}',
    'time','${ACTIVATED_AT}', 'datacontenttype','application/json',
    'orgmetratenant','${TENANT_ID}', 'orgmetraactor','${ACTOR_REFERENCE}',
    'orgmetrapurpose','performance_goal_plan_persistence',
    'orgmetrareason','activated_goal_plan_record', 'orgmetraevidence','${ACTIVATION_DIGEST}',
    'data',jsonb_build_object('high_impact',false,'result_code','activated_plan_persisted')
  )::text AS body
)
INSERT INTO audit_event_record (
  tenant_record_id, audit_event_record_id, canonical_event_json, event_envelope_digest
)
SELECT '${TENANT_ID}', '${AUDIT_ID}', body,
       encode(digest(convert_to(body,'UTF8'),'sha256'),'hex')
FROM event_payload;
INSERT INTO outbox_delivery_record (
  tenant_record_id, outbox_delivery_record_id, audit_event_record_id, delivery_target_code
) VALUES ('${TENANT_ID}', '${OUTBOX_ID}', '${AUDIT_ID}', 'integration_hub');

INSERT INTO performance_goal_plan_record (
  tenant_record_id, performance_goal_plan_record_id, performance_goal_plan_reference,
  employment_record_id, job_profile_id, performance_cycle_reference, created_by_actor_reference
) VALUES (
  '${TENANT_ID}', '${PLAN_RECORD_ID}', '${PLAN_REFERENCE}', '${EMPLOYMENT_ID}', '${JOB_ID}',
  '${CYCLE_REFERENCE}', '${ACTOR_REFERENCE}'
);
INSERT INTO performance_goal_plan_version (
  tenant_record_id, performance_goal_plan_version_id, performance_goal_plan_record_id,
  goal_set_digest_sha256, measurement_definition_digest_sha256, goal_count,
  feedback_cadence_code, plan_evidence_digest_sha256, activation_reference,
  activation_evidence_digest_sha256, authority_evidence_reference,
  authority_evidence_digest_sha256, approving_actor_reference, approved_at, activated_at,
  effective_from, effective_to, audit_event_record_id
) VALUES (
  '${TENANT_ID}', '${PLAN_VERSION_ID}', '${PLAN_RECORD_ID}', '${GOAL_DIGEST}',
  '${MEASUREMENT_DIGEST}', 3, 'quarterly_check_in', '${PLAN_DIGEST}', '${ACTIVATION_REFERENCE}',
  '${ACTIVATION_DIGEST}', '${AUTHORITY_REFERENCE}', '${AUTHORITY_DIGEST}', '${ACTOR_REFERENCE}',
  '${APPROVED_AT}', '${ACTIVATED_AT}', DATE '2026-09-01', DATE '2026-12-31', '${AUDIT_ID}'
);
SQL

persisted="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "
SELECT persistence_state || '|' || rating_authority_state || '|' || employment_decision_authority_state
FROM performance_goal_plan_version
WHERE performance_goal_plan_version_id='${PLAN_VERSION_ID}'::uuid;")"
[[ "${persisted}" == "authoritatively_persisted|not_authorized_for_performance_rating|not_authorized_for_employment_decision" ]] || {
  echo "performance-goal plan persisted unsafe state: ${persisted}" >&2; exit 1;
}

expect_failure "backdated system time accepted" "recorded_from must equal" "
INSERT INTO performance_goal_plan_version (
 tenant_record_id, performance_goal_plan_version_id, performance_goal_plan_record_id,
 goal_set_digest_sha256, measurement_definition_digest_sha256, goal_count, feedback_cadence_code,
 plan_evidence_digest_sha256, activation_reference, activation_evidence_digest_sha256,
 authority_evidence_reference, authority_evidence_digest_sha256, approving_actor_reference,
 approved_at, activated_at, effective_from, effective_to, audit_event_record_id, recorded_from
) VALUES (
 '${TENANT_ID}', '10000000-0000-7000-8000-000000000053', '${PLAN_RECORD_ID}', '${GOAL_DIGEST}',
 '${MEASUREMENT_DIGEST}', 3, 'quarterly_check_in', '${PLAN_DIGEST}',
 'performance_goal_activation:00000000-0000-4000-8000-000000000054', '${ACTIVATION_DIGEST}',
 '${AUTHORITY_REFERENCE}', '${AUTHORITY_DIGEST}', '${ACTOR_REFERENCE}', '${APPROVED_AT}', '${ACTIVATED_AT}',
 DATE '2026-09-01', DATE '2026-12-31', '${AUDIT_ID}', TIMESTAMPTZ '2000-01-01 00:00:00+00');"

expect_failure "mismatched activation audit accepted" "audit evidence does not match" "
INSERT INTO performance_goal_plan_version (
 tenant_record_id, performance_goal_plan_version_id, performance_goal_plan_record_id,
 goal_set_digest_sha256, measurement_definition_digest_sha256, goal_count, feedback_cadence_code,
 plan_evidence_digest_sha256, activation_reference, activation_evidence_digest_sha256,
 authority_evidence_reference, authority_evidence_digest_sha256, approving_actor_reference,
 approved_at, activated_at, effective_from, effective_to, audit_event_record_id
) VALUES (
 '${TENANT_ID}', '10000000-0000-7000-8000-000000000055', '${PLAN_RECORD_ID}', '${GOAL_DIGEST}',
 '${MEASUREMENT_DIGEST}', 3, 'quarterly_check_in', '${PLAN_DIGEST}',
 'performance_goal_activation:00000000-0000-4000-8000-000000000056',
 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
 '${AUTHORITY_REFERENCE}', '${AUTHORITY_DIGEST}', '${ACTOR_REFERENCE}', '${APPROVED_AT}', '${ACTIVATED_AT}',
 DATE '2026-09-01', DATE '2026-12-31', '${AUDIT_ID}');"

expect_failure "Job coverage gap accepted" "Job coverage" "
INSERT INTO performance_goal_plan_version (
 tenant_record_id, performance_goal_plan_version_id, performance_goal_plan_record_id,
 goal_set_digest_sha256, measurement_definition_digest_sha256, goal_count, feedback_cadence_code,
 plan_evidence_digest_sha256, activation_reference, activation_evidence_digest_sha256,
 authority_evidence_reference, authority_evidence_digest_sha256, approving_actor_reference,
 approved_at, activated_at, effective_from, effective_to, audit_event_record_id
) VALUES (
 '${TENANT_ID}', '10000000-0000-7000-8000-000000000057', '${PLAN_RECORD_ID}', '${GOAL_DIGEST}',
 '${MEASUREMENT_DIGEST}', 3, 'quarterly_check_in', '${PLAN_DIGEST}',
 'performance_goal_activation:00000000-0000-4000-8000-000000000058', '${ACTIVATION_DIGEST}',
 '${AUTHORITY_REFERENCE}', '${AUTHORITY_DIGEST}', '${ACTOR_REFERENCE}', '${APPROVED_AT}', '${ACTIVATED_AT}',
 DATE '2027-01-01', DATE '2027-01-15', '${AUDIT_ID}');"

expect_failure "Employment coverage gap accepted" "active or leave Employment coverage" "
INSERT INTO performance_goal_plan_version (
 tenant_record_id, performance_goal_plan_version_id, performance_goal_plan_record_id,
 goal_set_digest_sha256, measurement_definition_digest_sha256, goal_count, feedback_cadence_code,
 plan_evidence_digest_sha256, activation_reference, activation_evidence_digest_sha256,
 authority_evidence_reference, authority_evidence_digest_sha256, approving_actor_reference,
 approved_at, activated_at, effective_from, effective_to, audit_event_record_id
) VALUES (
 '${TENANT_ID}', '10000000-0000-7000-8000-000000000059', '${PLAN_RECORD_ID}', '${GOAL_DIGEST}',
 '${MEASUREMENT_DIGEST}', 3, 'quarterly_check_in', '${PLAN_DIGEST}',
 'performance_goal_activation:00000000-0000-4000-8000-000000000060', '${ACTIVATION_DIGEST}',
 '${AUTHORITY_REFERENCE}', '${AUTHORITY_DIGEST}', '${ACTOR_REFERENCE}', '${APPROVED_AT}', '${ACTIVATED_AT}',
 DATE '2028-02-01', DATE '2028-03-01', '${AUDIT_ID}');"

expect_failure "goal-plan evidence rewrite accepted" "immutable" "
UPDATE performance_goal_plan_version SET goal_set_digest_sha256 =
'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'
WHERE performance_goal_plan_version_id='${PLAN_VERSION_ID}'::uuid;"

with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
UPDATE performance_goal_plan_version SET recorded_to=pg_catalog.transaction_timestamp()
WHERE performance_goal_plan_version_id='${PLAN_VERSION_ID}'::uuid;"
expect_failure "goal-plan history deletion accepted" "immutable" "DELETE FROM performance_goal_plan_version WHERE performance_goal_plan_record_id='${PLAN_RECORD_ID}'::uuid;"
expect_failure "goal-plan history truncate accepted" "cannot be truncated" "TRUNCATE performance_goal_plan_version;"

for forbidden_column in goal_text performance_rating assessment_score compensation_value candidate_reference free_form_note prompt_text model_output; do
  count="$(psql "${DATABASE_URL}" -Atqc "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('performance_goal_plan_record','performance_goal_plan_version') AND column_name='${forbidden_column}';")"
  [[ "${count}" == "0" ]] || { echo "prohibited sensitive column exists: ${forbidden_column}" >&2; exit 1; }
done

rls_state="$(psql "${DATABASE_URL}" -Atqc "SELECT string_agg(relname || ':' || relrowsecurity::text || ':' || relforcerowsecurity::text, ',' ORDER BY relname) FROM pg_class WHERE relname IN ('performance_goal_plan_record','performance_goal_plan_version');")"
[[ "${rls_state}" == "performance_goal_plan_record:true:true,performance_goal_plan_version:true:true" ]] || { echo "goal-plan RLS is not forced: ${rls_state}" >&2; exit 1; }

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='performance_goal_reader') THEN
    CREATE ROLE performance_goal_reader NOSUPERUSER NOBYPASSRLS;
  END IF;
END $$;
GRANT SELECT ON performance_goal_plan_record, performance_goal_plan_version TO performance_goal_reader;
SQL

visible="$(psql "${DATABASE_URL}" -Atqc "BEGIN; SET LOCAL ROLE performance_goal_reader; SET LOCAL orgmetra.tenant_record_id='${TENANT_ID}'; SELECT count(*) FROM performance_goal_plan_record; COMMIT;" | tail -n 1)"
hidden="$(psql "${DATABASE_URL}" -Atqc "BEGIN; SET LOCAL ROLE performance_goal_reader; SET LOCAL orgmetra.tenant_record_id='${OTHER_TENANT_ID}'; SELECT count(*) FROM performance_goal_plan_record; COMMIT;" | tail -n 1)"
[[ "${visible}" == "1" && "${hidden}" == "0" ]] || { echo "tenant isolation failed: own=${visible} foreign=${hidden}" >&2; exit 1; }

printf '%s\n' "performance goal-plan persistence: PASS"
