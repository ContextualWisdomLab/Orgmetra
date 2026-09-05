#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

owner_migration="services/workforce-validation-api/database/migrations/0001_owner_schema.sql"
adoption_migration="services/workforce-validation-api/database/migrations/0002_registry_adoption.sql"
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${owner_migration}"

role_flags="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolinherit, rolreplication, rolbypassrls
FROM pg_roles
WHERE rolname = 'workforce_validation_role';
")"
if [[ "${role_flags}" != "f|f|f|f|f|f|f" ]]; then
    echo "workforce_validation_role flags are not deny-default: ${role_flags}" >&2
    exit 1
fi

schema_owner="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT pg_get_userbyid(nspowner)
FROM pg_namespace
WHERE nspname = 'workforce_validation';
")"
if [[ "${schema_owner}" != "workforce_validation_role" ]]; then
    echo "workforce_validation schema has unexpected owner: ${schema_owner}" >&2
    exit 1
fi

role_config="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT COALESCE(array_to_string(rolconfig, ','), '')
FROM pg_roles
WHERE rolname = 'workforce_validation_role';
")"
if [[ -n "${role_config}" ]]; then
    echo "NOLOGIN schema owner must not carry ineffective login-only runtime defaults: ${role_config}" >&2
    exit 1
fi

set_role_probe="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SET search_path = public;
SET ROLE workforce_validation_role;
SELECT current_user || '|' || current_setting('search_path');
RESET ROLE;
")"
if [[ "${set_role_probe}" != "workforce_validation_role|public" ]]; then
    echo "unexpected SET ROLE search_path behavior: ${set_role_probe}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -qc "CREATE ROLE workforce_validation_public_probe NOLOGIN;"
trap 'psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -qc "DROP ROLE IF EXISTS workforce_validation_public_probe;" >/dev/null 2>&1 || true' EXIT

public_usage="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT has_schema_privilege('workforce_validation_public_probe', 'workforce_validation', 'USAGE');
")"
public_create="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT has_schema_privilege('workforce_validation_public_probe', 'workforce_validation', 'CREATE');
")"
if [[ "${public_usage}" != "f" || "${public_create}" != "f" ]]; then
    echo "PUBLIC retains workforce_validation schema privileges: usage=${public_usage} create=${public_create}" >&2
    exit 1
fi

relation_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_class AS relation
JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
WHERE namespace.nspname = 'workforce_validation';
")"
if [[ "${relation_count}" != "0" ]]; then
    echo "owner-schema bootstrap created application relations prematurely: ${relation_count}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -qc "DROP ROLE workforce_validation_public_probe;"
trap - EXIT

# Adoption must be proven against the protected migration state that already owns
# the normalized validity-study case trigger. A table move is not complete if
# schema-qualified SQL inside that trigger still names the legacy relation.
for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0003_audit_outbox_persistence.sql \
    database/migrations/0004_outbox_delivery_claim.sql \
    database/migrations/0005_outbox_delivery_finalization.sql \
    database/migrations/0006_outbox_delivery_dead_letter.sql \
    database/migrations/0007_outbox_retry_exhaustion.sql \
    database/migrations/0008_audit_outbox_review_hardening.sql \
    database/migrations/0009_candidate_worker_conversion_governance.sql \
    database/migrations/0010_validity_study_case_integrity.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="10000000-0000-7000-8000-000000000001"
PERSON_ID="00000000-0000-7000-8000-000000000001"
EMPLOYMENT_ID="00000000-0000-7000-8000-000000000011"
JOB_ID="00000000-0000-7000-8000-000000000021"
CANDIDATE_ID="00000000-0000-7000-8000-000000000031"
EVIDENCE_ID="00000000-0000-7000-8000-000000000041"
DECISION_ID="00000000-0000-7000-8000-000000000051"
AUDIT_ID="00000000-0000-7000-8000-000000000062"
OUTBOX_ID="00000000-0000-7000-8000-000000000072"
CONVERSION_ID="00000000-0000-7000-8000-000000000081"
CYCLE_ID="00000000-0000-7000-8000-000000000091"
CRITERION_ID="00000000-0000-7000-8000-0000000000a1"
OBSERVATION_ID="00000000-0000-7000-8000-0000000000b1"
STUDY_ID="00000000-0000-7000-8000-0000000000c1"
CASE_ID="00000000-0000-7000-8000-0000000000e4"

tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}', 'tenant_alpha');

INSERT INTO person_record (tenant_record_id, person_record_id, recorded_from)
VALUES ('${TENANT_ID}', '${PERSON_ID}', TIMESTAMPTZ '2026-08-17 04:50:00+00');

INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id, recorded_from
) VALUES (
    '${TENANT_ID}', '${EMPLOYMENT_ID}', '${PERSON_ID}',
    TIMESTAMPTZ '2026-08-17 04:55:00+00'
);

INSERT INTO job_profile (tenant_record_id, job_profile_id, recorded_from)
VALUES ('${TENANT_ID}', '${JOB_ID}', TIMESTAMPTZ '2026-08-17 04:40:00+00');

INSERT INTO candidate_profile (
    tenant_record_id, candidate_profile_id, application_status_code, recorded_from
) VALUES (
    '${TENANT_ID}', '${CANDIDATE_ID}', 'offer',
    TIMESTAMPTZ '2026-08-17 04:45:00+00'
);

INSERT INTO decision_evidence_set (
    tenant_record_id, decision_evidence_set_id, evidence_set_version_code,
    digest_algorithm_code, created_at
) VALUES (
    '${TENANT_ID}', '${EVIDENCE_ID}', 'selection_packet_v3', 'sha256',
    TIMESTAMPTZ '2026-08-17 04:56:00+00'
);

INSERT INTO selection_decision_evidence (
    tenant_record_id, selection_decision_evidence_id, decision_evidence_set_id,
    evidence_reference, evidence_version_code, recorded_at
) VALUES (
    '${TENANT_ID}', '00000000-0000-7000-8000-000000000042', '${EVIDENCE_ID}',
    'structured_interview:panel_17', 'rubric_v5',
    TIMESTAMPTZ '2026-08-17 04:57:00+00'
);

INSERT INTO selection_decision (
    tenant_record_id, selection_decision_id, candidate_profile_id, job_profile_id,
    decision_evidence_set_id, actor_reference, purpose_code, decision_code,
    decision_reason, confirmation_reference, decided_at, recorded_at
) VALUES (
    '${TENANT_ID}', '${DECISION_ID}', '${CANDIDATE_ID}', '${JOB_ID}', '${EVIDENCE_ID}',
    'keyverse_subject:01JHIRINGMANAGER', 'talent_acquisition', 'hire',
    'Structured interview and verified role evidence supported hire',
    'confirmation:01JHUMANCONFIRM',
    TIMESTAMPTZ '2026-08-17 04:59:00+00',
    TIMESTAMPTZ '2026-08-17 05:00:00+00'
);

INSERT INTO performance_cycle (
    tenant_record_id, performance_cycle_id, cycle_name, cycle_status_code,
    effective_from, effective_to, recorded_from
) VALUES (
    '${TENANT_ID}', '${CYCLE_ID}', '2026 post-hire criterion window', 'cycle_closed',
    DATE '2026-10-01', DATE '2027-01-01',
    TIMESTAMPTZ '2026-10-01 00:00:00+00'
);

INSERT INTO criterion_blueprint (
    tenant_record_id, criterion_blueprint_id, job_profile_id,
    criterion_type_code, criterion_version_code, effective_from, recorded_from
) VALUES (
    '${TENANT_ID}', '${CRITERION_ID}', '${JOB_ID}',
    'supervisor_performance', 'criterion_v1', DATE '2026-10-01',
    TIMESTAMPTZ '2026-10-01 00:00:00+00'
);

INSERT INTO criterion_observation (
    tenant_record_id, criterion_observation_id, criterion_blueprint_id,
    performance_cycle_id, person_record_id, observed_value,
    observed_at, recorded_from, recorded_to
) VALUES (
    '${TENANT_ID}', '${OBSERVATION_ID}', '${CRITERION_ID}', '${CYCLE_ID}', '${PERSON_ID}',
    4.4, TIMESTAMPTZ '2026-11-01 12:00:00+00',
    TIMESTAMPTZ '2026-11-02 09:00:00+00', NULL
);

INSERT INTO validity_study (
    tenant_record_id, validity_study_id, criterion_blueprint_id,
    study_status_code, recorded_from
) VALUES (
    '${TENANT_ID}', '${STUDY_ID}', '${CRITERION_ID}', 'study_draft',
    TIMESTAMPTZ '2026-11-03 00:00:00+00'
);
SQL

good_audit_event='{"data":{"high_impact":true,"result_code":"worker_created"},"datacontenttype":"application/json","id":"00000000-0000-7000-8000-000000000062","orgmetraactor":"keyverse_subject:01JHIRINGMANAGER","orgmetraconfirmation":"confirmation:01JHUMANCONFIRM","orgmetraevidence":"decision_evidence_set:00000000-0000-7000-8000-000000000041","orgmetrapurpose":"talent_acquisition","orgmetrareason":"candidate_hire_confirmed","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:talent_core","specversion":"1.0","subject":"candidate_worker_conversion_record:00000000-0000-7000-8000-000000000081","time":"2026-08-17T05:01:00Z","type":"orgmetra.candidate.worker_converted"}'

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v canonical_event="${good_audit_event}" <<SQL
SELECT record_audit_outbox_event(
    '${TENANT_ID}'::uuid,
    '${AUDIT_ID}'::uuid,
    '${OUTBOX_ID}'::uuid,
    :'canonical_event',
    encode(digest(convert_to(:'canonical_event', 'UTF8'), 'sha256'), 'hex'),
    'talent_event_sink'
);

INSERT INTO candidate_worker_conversion_record (
    tenant_record_id, candidate_worker_conversion_record_id, candidate_profile_id,
    person_record_id, employment_record_id, selection_decision_id,
    audit_event_record_id, effective_from, recorded_from
) VALUES (
    '${TENANT_ID}', '${CONVERSION_ID}', '${CANDIDATE_ID}', '${PERSON_ID}', '${EMPLOYMENT_ID}',
    '${DECISION_ID}', '${AUDIT_ID}', DATE '2026-08-17',
    TIMESTAMPTZ '2026-08-17 05:02:00+00'
);
SQL

legacy_oid="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "SELECT 'public.validity_study'::regclass::oid;")"
legacy_fk_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*) FROM pg_constraint WHERE contype = 'f' AND confrelid = ${legacy_oid};
")"
if [[ "${legacy_fk_count}" != "4" ]]; then
    echo "unexpected protected FK dependency count before adoption: ${legacy_fk_count}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${adoption_migration}"

if [[ "$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "SELECT to_regclass('public.validity_study') IS NULL;")" != "t" ]]; then
    echo "legacy public.validity_study relation still exists after owner adoption" >&2
    exit 1
fi

owner_oid="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "SELECT 'workforce_validation.validity_study'::regclass::oid;")"
if [[ "${owner_oid}" != "${legacy_oid}" ]]; then
    echo "registry adoption copied/recreated the table instead of preserving relation identity" >&2
    exit 1
fi

registry_owner="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT pg_get_userbyid(relowner)
FROM pg_class
WHERE oid = ${owner_oid};
")"
if [[ "${registry_owner}" != "workforce_validation_role" ]]; then
    echo "registry table has unexpected owner: ${registry_owner}" >&2
    exit 1
fi

owner_fk_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*) FROM pg_constraint WHERE contype = 'f' AND confrelid = ${owner_oid};
")"
if [[ "${owner_fk_count}" != "${legacy_fk_count}" ]]; then
    echo "registry adoption broke existing FK dependencies: before=${legacy_fk_count} after=${owner_fk_count}" >&2
    exit 1
fi

rls_flags="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT relrowsecurity, relforcerowsecurity
FROM pg_class
WHERE oid = ${owner_oid};
")"
if [[ "${rls_flags}" != "t|t" ]]; then
    echo "registry adoption did not preserve forced tenant RLS: ${rls_flags}" >&2
    exit 1
fi

bitemporal_trigger="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_trigger
WHERE tgrelid = ${owner_oid}
  AND tgname = 'validity_study_bitemporal_guard'
  AND NOT tgisinternal;
")"
if [[ "${bitemporal_trigger}" != "1" ]]; then
    echo "registry adoption lost the bitemporal mutation guard" >&2
    exit 1
fi

# Regression for #251: the normalized case-governance trigger must remain
# executable after the registry table moves out of public. The predecessor
# function body names public.validity_study and therefore fails this insert.
tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO public.validity_study_case_record (
    tenant_record_id, validity_study_case_record_id, validity_study_id,
    selection_decision_id, decision_evidence_set_id, criterion_observation_id,
    candidate_worker_conversion_record_id, linked_at
) VALUES (
    '${TENANT_ID}', '${CASE_ID}', '${STUDY_ID}', '${DECISION_ID}', '${EVIDENCE_ID}',
    '${OBSERVATION_ID}', '${CONVERSION_ID}', TIMESTAMPTZ '2026-11-03 01:00:00+00'
);
SQL

case_count="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM public.validity_study_case_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND validity_study_case_record_id = '${CASE_ID}'::uuid;
")"
if [[ "${case_count}" != "1" ]]; then
    echo "governed validity-study case did not persist after registry adoption" >&2
    exit 1
fi

runtime_flags="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolinherit, rolreplication, rolbypassrls
FROM pg_roles
WHERE rolname = 'workforce_validation_runtime_role';
")"
if [[ "${runtime_flags}" != "f|f|f|f|f|f|f" ]]; then
    echo "workforce_validation_runtime_role flags are not deny-default: ${runtime_flags}" >&2
    exit 1
fi

runtime_privileges="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT
  has_schema_privilege('workforce_validation_runtime_role', 'workforce_validation', 'USAGE'),
  has_schema_privilege('workforce_validation_runtime_role', 'workforce_validation', 'CREATE'),
  has_table_privilege('workforce_validation_runtime_role', 'workforce_validation.validity_study', 'SELECT'),
  has_table_privilege('workforce_validation_runtime_role', 'workforce_validation.validity_study', 'INSERT'),
  has_table_privilege('workforce_validation_runtime_role', 'workforce_validation.validity_study', 'UPDATE'),
  has_table_privilege('workforce_validation_runtime_role', 'workforce_validation.validity_study', 'DELETE'),
  has_table_privilege('workforce_validation_runtime_role', 'workforce_validation.validity_study', 'TRUNCATE');
")"
if [[ "${runtime_privileges}" != "t|f|t|f|f|f|f" ]]; then
    echo "runtime role privileges are not least-privilege read-only: ${runtime_privileges}" >&2
    exit 1
fi

missing_tenant_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SET ROLE workforce_validation_runtime_role;
SELECT count(*) FROM workforce_validation.validity_study;
RESET ROLE;
")"
if [[ "${missing_tenant_count}" != "0" ]]; then
    echo "runtime read returned rows without tenant context: ${missing_tenant_count}" >&2
    exit 1
fi

tenant_read="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SET orgmetra.tenant_record_id = '${TENANT_ID}';
SET ROLE workforce_validation_runtime_role;
SELECT validity_study_id::text FROM workforce_validation.validity_study;
RESET ROLE;
RESET orgmetra.tenant_record_id;
")"
if [[ "${tenant_read}" != "${STUDY_ID}" ]]; then
    echo "runtime role did not read the tenant-scoped owner registry: ${tenant_read}" >&2
    exit 1
fi
