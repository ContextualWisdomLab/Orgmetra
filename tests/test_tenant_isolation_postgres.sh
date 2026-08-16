#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES
  ('10000000-0000-7000-8000-000000000001', 'tenant_alpha'),
  ('20000000-0000-7000-8000-000000000001', 'tenant_beta');

INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES ('10000000-0000-7000-8000-000000000001', '00000000-0000-7000-8000-000000000001');
INSERT INTO person_name_record (
    tenant_record_id, person_name_record_id, person_record_id, display_name,
    effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000002',
    '00000000-0000-7000-8000-000000000001',
    'Ada Lovelace', DATE '2026-01-01', TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id,
    employment_status_code, effective_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000003',
    '00000000-0000-7000-8000-000000000001',
    'active', DATE '2026-01-01'
);
INSERT INTO organization_unit (tenant_record_id, organization_unit_id)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000004'
);
INSERT INTO organization_unit_version (
    tenant_record_id, organization_unit_version_id, organization_unit_id,
    unit_name, organization_type_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000005',
    '00000000-0000-7000-8000-000000000004',
    'People', 'department', DATE '2026-01-01', TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
INSERT INTO job_profile (tenant_record_id, job_profile_id)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000006'
);
INSERT INTO job_profile_version (
    tenant_record_id, job_profile_version_id, job_profile_id, job_title,
    job_family_code, job_version_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000007',
    '00000000-0000-7000-8000-000000000006',
    'Principal AI Product Architect', 'product', '2026.1', DATE '2026-01-01',
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
INSERT INTO position_record (
    tenant_record_id, position_record_id, organization_unit_id, job_profile_id,
    position_status_code, effective_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000008',
    '00000000-0000-7000-8000-000000000004',
    '00000000-0000-7000-8000-000000000006',
    'active', DATE '2026-01-01'
);
INSERT INTO assignment_record (
    tenant_record_id, assignment_record_id, person_record_id, position_record_id,
    allocation_ratio, effective_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000009',
    '00000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000008', 1.0, DATE '2026-01-01'
);
INSERT INTO candidate_profile (
    tenant_record_id, candidate_profile_id, application_status_code
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000010', 'converted'
);
INSERT INTO candidate_worker_link (
    tenant_record_id, candidate_worker_link_id, candidate_profile_id, person_record_id
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000011',
    '00000000-0000-7000-8000-000000000010',
    '00000000-0000-7000-8000-000000000001'
);
INSERT INTO performance_cycle (
    tenant_record_id, performance_cycle_id, cycle_name, cycle_status_code, effective_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000012', '2026 Annual', 'active', DATE '2026-01-01'
);
INSERT INTO criterion_blueprint (
    tenant_record_id, criterion_blueprint_id, job_profile_id, criterion_type_code,
    criterion_version_code, effective_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000013',
    '00000000-0000-7000-8000-000000000006', 'performance', '2026.1', DATE '2026-01-01'
);
INSERT INTO criterion_observation (
    tenant_record_id, criterion_observation_id, criterion_blueprint_id,
    performance_cycle_id, person_record_id, observed_value, observed_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000014',
    '00000000-0000-7000-8000-000000000013',
    '00000000-0000-7000-8000-000000000012',
    '00000000-0000-7000-8000-000000000001', 4.5,
    TIMESTAMPTZ '2026-06-30 00:00:00+00'
);
INSERT INTO decision_evidence_set (
    tenant_record_id, decision_evidence_set_id, evidence_set_version_code,
    digest_algorithm_code
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000015', 'v1', 'sha256'
);
INSERT INTO selection_decision_evidence (
    tenant_record_id, selection_decision_evidence_id, decision_evidence_set_id,
    evidence_reference, evidence_version_code
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000016',
    '00000000-0000-7000-8000-000000000015', 'evidence://assessment/1', '2026.1'
);
INSERT INTO selection_decision (
    tenant_record_id, selection_decision_id, candidate_profile_id, job_profile_id,
    decision_evidence_set_id, actor_reference, purpose_code, decision_code,
    decision_reason, confirmation_reference, decided_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000017',
    '00000000-0000-7000-8000-000000000010',
    '00000000-0000-7000-8000-000000000006',
    '00000000-0000-7000-8000-000000000015',
    'actor://hr/1', 'selection_review', 'hire', 'Human-confirmed evidence review.',
    'confirmation://workflow/1', TIMESTAMPTZ '2026-07-01 00:00:00+00'
);
INSERT INTO validity_study (
    tenant_record_id, validity_study_id, criterion_blueprint_id, study_status_code
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000018',
    '00000000-0000-7000-8000-000000000013', 'active'
);
INSERT INTO validity_study_decision_link (
    tenant_record_id, validity_study_decision_link_id, validity_study_id,
    selection_decision_id
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000019',
    '00000000-0000-7000-8000-000000000018',
    '00000000-0000-7000-8000-000000000017'
);
INSERT INTO validity_study_outcome_link (
    tenant_record_id, validity_study_outcome_link_id, validity_study_id,
    criterion_observation_id
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000020',
    '00000000-0000-7000-8000-000000000018',
    '00000000-0000-7000-8000-000000000014'
);
INSERT INTO validity_study_evidence_set_link (
    tenant_record_id, validity_study_evidence_set_link_id, validity_study_id,
    decision_evidence_set_id
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000021',
    '00000000-0000-7000-8000-000000000018',
    '00000000-0000-7000-8000-000000000015'
);
INSERT INTO compensation_record (
    tenant_record_id, compensation_record_id, person_record_id, amount_value,
    currency_code, effective_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000022',
    '00000000-0000-7000-8000-000000000001', 100000, 'USD', DATE '2026-01-01'
);
INSERT INTO employment_transition (
    tenant_record_id, employment_transition_id, employment_record_id,
    transition_type_code, effective_date
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000023',
    '00000000-0000-7000-8000-000000000003', 'hire', DATE '2026-01-01'
);
SQL

set +e
cross_tenant_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id,
    employment_status_code, effective_from
) VALUES (
    '20000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000030',
    '00000000-0000-7000-8000-000000000001',
    'active', DATE '2026-01-01'
);
SQL
} 2>&1)"
cross_tenant_status=$?
set -e
if [[ ${cross_tenant_status} -eq 0 ]]; then
    echo "cross-tenant foreign-key reference unexpectedly succeeded" >&2
    exit 1
fi
if [[ "${cross_tenant_output}" != *"foreign key constraint"* ]]; then
    echo "cross-tenant write failed for an unexpected reason: ${cross_tenant_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE orgmetra_tenant_writer NOLOGIN NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO orgmetra_tenant_writer;
GRANT INSERT ON person_record TO orgmetra_tenant_writer;
SQL

set +e
missing_context_write_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
SET ROLE orgmetra_tenant_writer;
INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000040'
);
SQL
} 2>&1)"
missing_context_write_status=$?
set -e
if [[ ${missing_context_write_status} -eq 0 ]]; then
    echo "NOBYPASSRLS writer inserted without tenant context" >&2
    exit 1
fi
if [[ "${missing_context_write_output}" != *"row-level security policy"* ]]; then
    echo "missing-context write failed for an unexpected reason: ${missing_context_write_output}" >&2
    exit 1
fi

set +e
cross_context_write_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
SET ROLE orgmetra_tenant_writer;
SET orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES (
    '20000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000041'
);
SQL
} 2>&1)"
cross_context_write_status=$?
set -e
if [[ ${cross_context_write_status} -eq 0 ]]; then
    echo "NOBYPASSRLS writer inserted a different tenant under tenant-alpha context" >&2
    exit 1
fi
if [[ "${cross_context_write_output}" != *"row-level security policy"* ]]; then
    echo "cross-context write failed for an unexpected reason: ${cross_context_write_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE orgmetra_tenant_reader NOLOGIN NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO orgmetra_tenant_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO orgmetra_tenant_reader;
SET ROLE orgmetra_tenant_reader;

DO $$
DECLARE
    table_name text;
    visible_count bigint;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'tenant_record', 'person_record', 'person_name_record', 'employment_record',
        'organization_unit', 'organization_unit_version', 'job_profile',
        'job_profile_version', 'position_record', 'assignment_record',
        'candidate_profile', 'candidate_worker_link', 'performance_cycle',
        'criterion_blueprint', 'criterion_observation', 'decision_evidence_set',
        'selection_decision_evidence', 'selection_decision', 'validity_study',
        'validity_study_decision_link', 'validity_study_outcome_link',
        'validity_study_evidence_set_link', 'compensation_record',
        'employment_transition'
    ]
    LOOP
        EXECUTE format('SELECT count(*) FROM %I', table_name) INTO visible_count;
        IF visible_count <> 0 THEN
            RAISE EXCEPTION 'missing tenant context exposed % row(s) from %', visible_count, table_name;
        END IF;
    END LOOP;
END;
$$;

SET orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
DO $$
DECLARE
    table_name text;
    visible_count bigint;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'tenant_record', 'person_record', 'person_name_record', 'employment_record',
        'organization_unit', 'organization_unit_version', 'job_profile',
        'job_profile_version', 'position_record', 'assignment_record',
        'candidate_profile', 'candidate_worker_link', 'performance_cycle',
        'criterion_blueprint', 'criterion_observation', 'decision_evidence_set',
        'selection_decision_evidence', 'selection_decision', 'validity_study',
        'validity_study_decision_link', 'validity_study_outcome_link',
        'validity_study_evidence_set_link', 'compensation_record',
        'employment_transition'
    ]
    LOOP
        EXECUTE format('SELECT count(*) FROM %I', table_name) INTO visible_count;
        IF visible_count <> 1 THEN
            RAISE EXCEPTION 'tenant alpha expected exactly one row from %, got %', table_name, visible_count;
        END IF;
    END LOOP;
END;
$$;

SET orgmetra.tenant_record_id = '20000000-0000-7000-8000-000000000001';
DO $$
DECLARE
    table_name text;
    visible_count bigint;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'person_record', 'person_name_record', 'employment_record',
        'organization_unit', 'organization_unit_version', 'job_profile',
        'job_profile_version', 'position_record', 'assignment_record',
        'candidate_profile', 'candidate_worker_link', 'performance_cycle',
        'criterion_blueprint', 'criterion_observation', 'decision_evidence_set',
        'selection_decision_evidence', 'selection_decision', 'validity_study',
        'validity_study_decision_link', 'validity_study_outcome_link',
        'validity_study_evidence_set_link', 'compensation_record',
        'employment_transition'
    ]
    LOOP
        EXECUTE format('SELECT count(*) FROM %I', table_name) INTO visible_count;
        IF visible_count <> 0 THEN
            RAISE EXCEPTION 'tenant beta observed % row(s) from tenant alpha in %', visible_count, table_name;
        END IF;
    END LOOP;
END;
$$;

RESET ROLE;
SQL

echo "PostgreSQL tenant-isolation contract passed"
