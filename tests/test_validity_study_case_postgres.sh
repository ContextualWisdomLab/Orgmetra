#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

# Reuse the exact candidate->worker governed fixture so criterion outcomes can be
# bound to a real human-confirmed hire and its current bitemporal conversion.
bash tests/test_candidate_worker_conversion_postgres.sh
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
  -f database/migrations/0010_validity_study_case_integrity.sql

TENANT_ID="10000000-0000-7000-8000-000000000001"
tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO person_record (
    tenant_record_id, person_record_id, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000002',
    TIMESTAMPTZ '2026-08-20 00:00:00+00'
);

INSERT INTO performance_cycle (
    tenant_record_id, performance_cycle_id, cycle_name, cycle_status_code,
    effective_from, effective_to, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000091',
    '2026 post-hire criterion window',
    'cycle_closed',
    DATE '2026-10-01', DATE '2027-01-01',
    TIMESTAMPTZ '2026-10-01 00:00:00+00'
);

INSERT INTO criterion_blueprint (
    tenant_record_id, criterion_blueprint_id, job_profile_id,
    criterion_type_code, criterion_version_code,
    effective_from, recorded_from
) VALUES
(
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-0000000000a1',
    '00000000-0000-7000-8000-000000000021',
    'supervisor_performance', 'criterion_v1',
    DATE '2026-10-01', TIMESTAMPTZ '2026-10-01 00:00:00+00'
),
(
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-0000000000a2',
    '00000000-0000-7000-8000-000000000021',
    'training_completion', 'criterion_v1',
    DATE '2026-10-01', TIMESTAMPTZ '2026-10-01 00:00:00+00'
);

INSERT INTO criterion_observation (
    tenant_record_id, criterion_observation_id, criterion_blueprint_id,
    performance_cycle_id, person_record_id, observed_value,
    observed_at, recorded_from
) VALUES
(
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-0000000000b1',
    '00000000-0000-7000-8000-0000000000a1',
    '00000000-0000-7000-8000-000000000091',
    '00000000-0000-7000-8000-000000000001',
    4.4, TIMESTAMPTZ '2026-11-01 12:00:00+00',
    TIMESTAMPTZ '2026-11-02 09:00:00+00'
),
(
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-0000000000b2',
    '00000000-0000-7000-8000-0000000000a2',
    '00000000-0000-7000-8000-000000000091',
    '00000000-0000-7000-8000-000000000001',
    0.9, TIMESTAMPTZ '2026-11-01 12:00:00+00',
    TIMESTAMPTZ '2026-11-02 09:00:00+00'
),
(
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-0000000000b3',
    '00000000-0000-7000-8000-0000000000a1',
    '00000000-0000-7000-8000-000000000091',
    '00000000-0000-7000-8000-000000000002',
    4.8, TIMESTAMPTZ '2026-11-01 12:00:00+00',
    TIMESTAMPTZ '2026-11-02 09:00:00+00'
);

INSERT INTO validity_study (
    tenant_record_id, validity_study_id, criterion_blueprint_id,
    study_status_code, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-0000000000c1',
    '00000000-0000-7000-8000-0000000000a1',
    'study_draft', TIMESTAMPTZ '2026-11-03 00:00:00+00'
);

INSERT INTO decision_evidence_set (
    tenant_record_id, decision_evidence_set_id, evidence_set_version_code,
    digest_algorithm_code, created_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-0000000000d1',
    'unrelated_open_set_v1', 'sha256',
    TIMESTAMPTZ '2026-11-03 00:00:00+00'
);
SQL

assert_rejected() {
    local expected="$1"
    shift
    set +e
    local output
    output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "$*"; } 2>&1)"
    local status=$?
    set -e
    if [[ ${status} -eq 0 ]]; then
        echo "expected rejection but statement succeeded: $*" >&2
        exit 1
    fi
    if [[ "${output}" != *"${expected}"* ]]; then
        echo "statement failed for an unexpected reason: ${output}" >&2
        exit 1
    fi
}

# The former three independent link tables could mix unrelated study membership.
# New writes must fail closed so every new case goes through one normalized row.
assert_rejected "legacy validity-study links are read-only" \
  "INSERT INTO validity_study_decision_link (tenant_record_id, validity_study_decision_link_id, validity_study_id, selection_decision_id) VALUES ('${TENANT_ID}', '00000000-0000-7000-8000-0000000000f1', '00000000-0000-7000-8000-0000000000c1', '00000000-0000-7000-8000-000000000051');"
assert_rejected "legacy validity-study links are read-only" \
  "INSERT INTO validity_study_outcome_link (tenant_record_id, validity_study_outcome_link_id, validity_study_id, criterion_observation_id) VALUES ('${TENANT_ID}', '00000000-0000-7000-8000-0000000000f2', '00000000-0000-7000-8000-0000000000c1', '00000000-0000-7000-8000-0000000000b1');"
assert_rejected "legacy validity-study links are read-only" \
  "INSERT INTO validity_study_evidence_set_link (tenant_record_id, validity_study_evidence_set_link_id, validity_study_id, decision_evidence_set_id) VALUES ('${TENANT_ID}', '00000000-0000-7000-8000-0000000000f3', '00000000-0000-7000-8000-0000000000c1', '00000000-0000-7000-8000-000000000041');"

assert_rejected "validity-study case requires the selection decision's exact evidence set" \
  "INSERT INTO validity_study_case_record (tenant_record_id, validity_study_case_record_id, validity_study_id, selection_decision_id, decision_evidence_set_id, criterion_observation_id, candidate_worker_conversion_record_id, linked_at) VALUES ('${TENANT_ID}', '00000000-0000-7000-8000-0000000000e1', '00000000-0000-7000-8000-0000000000c1', '00000000-0000-7000-8000-000000000051', '00000000-0000-7000-8000-0000000000d1', '00000000-0000-7000-8000-0000000000b1', '00000000-0000-7000-8000-000000000082', TIMESTAMPTZ '2026-11-03 01:00:00+00');"

assert_rejected "validity-study case outcome uses a different criterion" \
  "INSERT INTO validity_study_case_record (tenant_record_id, validity_study_case_record_id, validity_study_id, selection_decision_id, decision_evidence_set_id, criterion_observation_id, candidate_worker_conversion_record_id, linked_at) VALUES ('${TENANT_ID}', '00000000-0000-7000-8000-0000000000e2', '00000000-0000-7000-8000-0000000000c1', '00000000-0000-7000-8000-000000000051', '00000000-0000-7000-8000-000000000041', '00000000-0000-7000-8000-0000000000b2', '00000000-0000-7000-8000-000000000082', TIMESTAMPTZ '2026-11-03 01:00:00+00');"

assert_rejected "validity-study case outcome belongs to a different worker" \
  "INSERT INTO validity_study_case_record (tenant_record_id, validity_study_case_record_id, validity_study_id, selection_decision_id, decision_evidence_set_id, criterion_observation_id, candidate_worker_conversion_record_id, linked_at) VALUES ('${TENANT_ID}', '00000000-0000-7000-8000-0000000000e3', '00000000-0000-7000-8000-0000000000c1', '00000000-0000-7000-8000-000000000051', '00000000-0000-7000-8000-000000000041', '00000000-0000-7000-8000-0000000000b3', '00000000-0000-7000-8000-000000000082', TIMESTAMPTZ '2026-11-03 01:00:00+00');"

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO validity_study_case_record (
    tenant_record_id, validity_study_case_record_id, validity_study_id,
    selection_decision_id, decision_evidence_set_id, criterion_observation_id,
    candidate_worker_conversion_record_id, linked_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-0000000000e4',
    '00000000-0000-7000-8000-0000000000c1',
    '00000000-0000-7000-8000-000000000051',
    '00000000-0000-7000-8000-000000000041',
    '00000000-0000-7000-8000-0000000000b1',
    '00000000-0000-7000-8000-000000000082',
    TIMESTAMPTZ '2026-11-03 01:00:00+00'
);
SQL

case_count="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM validity_study_case_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND validity_study_case_record_id = '00000000-0000-7000-8000-0000000000e4'::uuid;
")"
if [[ "${case_count}" != "1" ]]; then
    echo "governed validity-study case was not persisted" >&2
    exit 1
fi

assert_rejected "append-only relation cannot be updated or deleted" \
  "UPDATE validity_study_case_record SET linked_at = TIMESTAMPTZ '2026-11-03 02:00:00+00' WHERE validity_study_case_record_id = '00000000-0000-7000-8000-0000000000e4';"
assert_rejected "validity-study case history cannot be truncated" \
  "TRUNCATE TABLE validity_study_case_record;"

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE orgmetra_validity_case_reader NOLOGIN NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO orgmetra_validity_case_reader;
GRANT SELECT ON validity_study_case_record TO orgmetra_validity_case_reader;
SET ROLE orgmetra_validity_case_reader;

DO $$
DECLARE visible_count bigint;
BEGIN
    PERFORM set_config('orgmetra.tenant_record_id', '', false);
    SELECT count(*) INTO visible_count FROM validity_study_case_record;
    IF visible_count <> 0 THEN
        RAISE EXCEPTION 'missing tenant context exposed validity-study cases';
    END IF;
END;
$$;

SET orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
DO $$
DECLARE visible_count bigint;
BEGIN
    SELECT count(*) INTO visible_count FROM validity_study_case_record;
    IF visible_count <> 1 THEN
        RAISE EXCEPTION 'tenant alpha did not see its governed validity-study case';
    END IF;
END;
$$;

SET orgmetra.tenant_record_id = '20000000-0000-7000-8000-000000000001';
DO $$
DECLARE visible_count bigint;
BEGIN
    SELECT count(*) INTO visible_count FROM validity_study_case_record;
    IF visible_count <> 0 THEN
        RAISE EXCEPTION 'foreign tenant context exposed validity-study cases';
    END IF;
END;
$$;

RESET ROLE;
SQL
