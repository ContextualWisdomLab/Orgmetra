#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

# Apply the exact migration set present on this candidate branch. The RED
# baseline does not contain the job-analysis migration, so the first governed
# source insert below fails until production support exists.
for migration in database/migrations/*.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="20000000-0000-7000-8000-000000000201"
OTHER_TENANT_ID="20000000-0000-7000-8000-000000000301"
tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES
    ('20000000-0000-7000-8000-000000000201', 'job_analysis_tenant'),
    ('20000000-0000-7000-8000-000000000301', 'foreign_job_analysis_tenant');

INSERT INTO job_profile (
    tenant_record_id, job_profile_id, recorded_from
) VALUES
    (
        '20000000-0000-7000-8000-000000000201',
        '20000000-0000-7000-8000-000000000202',
        TIMESTAMPTZ '2026-08-01 00:00:00+00'
    ),
    (
        '20000000-0000-7000-8000-000000000301',
        '20000000-0000-7000-8000-000000000302',
        TIMESTAMPTZ '2026-08-01 00:00:00+00'
    );

INSERT INTO source_record (
    tenant_record_id, source_record_id, source_type_code,
    source_locator, source_title, publisher_name, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000203',
    'web_authoritative',
    'https://www.opm.gov/policy-data-oversight/assessment-and-selection/job-analysis/',
    'Job analysis',
    'U.S. Office of Personnel Management',
    TIMESTAMPTZ '2026-08-18 00:00:00+00'
);

INSERT INTO source_version (
    tenant_record_id, source_version_id, source_record_id,
    source_version_code, source_content_sha256, captured_at, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000204',
    '20000000-0000-7000-8000-000000000203',
    'retrieved_2026_08_18',
    repeat('a', 64),
    TIMESTAMPTZ '2026-08-18 00:00:00+00',
    TIMESTAMPTZ '2026-08-18 00:00:01+00'
);

INSERT INTO job_analysis_case (
    tenant_record_id, job_analysis_case_id, job_profile_id,
    analysis_version_code, analysis_method_code, analyst_reference,
    effective_from, effective_to, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000205',
    '20000000-0000-7000-8000-000000000202',
    'analysis_v1',
    'functional_job_analysis',
    'analyst:job_architecture_001',
    DATE '2026-08-01',
    NULL,
    TIMESTAMPTZ '2026-08-18 00:01:00+00'
);

INSERT INTO job_analysis_source_link (
    tenant_record_id, job_analysis_source_link_id, job_analysis_case_id,
    source_version_id, evidence_role_code, source_span_reference, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000206',
    '20000000-0000-7000-8000-000000000205',
    '20000000-0000-7000-8000-000000000204',
    'task_basis',
    'section:job-analysis-overview',
    TIMESTAMPTZ '2026-08-18 00:02:00+00'
);

INSERT INTO task_statement (
    tenant_record_id, task_statement_id, job_analysis_case_id,
    task_sequence_number, task_text, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000207',
    '20000000-0000-7000-8000-000000000205',
    1,
    'Evaluate governed employment evidence against the approved decision policy.',
    TIMESTAMPTZ '2026-08-18 00:03:00+00'
);

INSERT INTO task_rating (
    tenant_record_id, task_rating_id, task_statement_id,
    rating_dimension_code, rating_value, scale_minimum_value,
    scale_maximum_value, rater_group_code, sample_size_count, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000208',
    '20000000-0000-7000-8000-000000000207',
    'importance',
    4.5,
    1.0,
    5.0,
    'subject_matter_experts',
    12,
    TIMESTAMPTZ '2026-08-18 00:04:00+00'
);

INSERT INTO fja_function (
    tenant_record_id, fja_function_id, job_analysis_case_id,
    function_dimension_code, function_level_value,
    methodology_version_code, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000209',
    '20000000-0000-7000-8000-000000000205',
    'data',
    5.0,
    'fja_v1',
    TIMESTAMPTZ '2026-08-18 00:05:00+00'
);

INSERT INTO task_fja_link (
    tenant_record_id, task_fja_link_id, task_statement_id,
    fja_function_id, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000210',
    '20000000-0000-7000-8000-000000000207',
    '20000000-0000-7000-8000-000000000209',
    TIMESTAMPTZ '2026-08-18 00:06:00+00'
);

INSERT INTO ksao_requirement (
    tenant_record_id, ksao_requirement_id, job_analysis_case_id,
    ksao_type_code, requirement_text, required_at_entry,
    recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000211',
    '20000000-0000-7000-8000-000000000205',
    'knowledge',
    'Knowledge of evidence-governance and employment decision controls.',
    true,
    TIMESTAMPTZ '2026-08-18 00:07:00+00'
);

INSERT INTO task_ksao_link (
    tenant_record_id, task_ksao_link_id, task_statement_id,
    ksao_requirement_id, linkage_strength_value, linkage_method_code,
    recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000212',
    '20000000-0000-7000-8000-000000000207',
    '20000000-0000-7000-8000-000000000211',
    4.0,
    'sme_rating',
    TIMESTAMPTZ '2026-08-18 00:08:00+00'
);

INSERT INTO job_analysis_approval_record (
    tenant_record_id, job_analysis_approval_record_id, job_analysis_case_id,
    approver_reference, approval_reason, evidence_version_code, approved_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000213',
    '20000000-0000-7000-8000-000000000205',
    'sme_panel:job_architecture_review_001',
    'Tasks, FJA functions, KSAOs, ratings, and authoritative source evidence were reviewed.',
    'approval_v1',
    TIMESTAMPTZ '2026-08-18 00:09:00+00'
);

DO $$
DECLARE
    observed_digest text;
BEGIN
    SELECT analysis_content_sha256
    INTO observed_digest
    FROM job_analysis_approval_record
    WHERE tenant_record_id = '20000000-0000-7000-8000-000000000201'
      AND job_analysis_case_id = '20000000-0000-7000-8000-000000000205';

    IF observed_digest !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'approved job analysis did not receive a database-owned SHA-256 digest';
    END IF;
END;
$$;
SQL

# Once approved, the analysis snapshot is sealed: appending another task would
# alter what the approval meant and must fail closed.
set +e
sealed_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO task_statement (
    tenant_record_id, task_statement_id, job_analysis_case_id,
    task_sequence_number, task_text, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000214',
    '20000000-0000-7000-8000-000000000205',
    2,
    'This task must not be appended after approval.',
    TIMESTAMPTZ '2026-08-18 00:10:00+00'
);
SQL
} 2>&1)"
sealed_status=$?
set -e
if [[ ${sealed_status} -eq 0 ]]; then
    echo "approved job analysis accepted post-approval task drift" >&2
    exit 1
fi
if [[ "${sealed_output}" != *"approved job analysis case is sealed"* ]]; then
    echo "post-approval task drift failed for an unexpected reason: ${sealed_output}" >&2
    exit 1
fi

# A second case with evidence and a task but no task↔FJA or task↔KSAO links
# must not be approvable.
tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO job_analysis_case (
    tenant_record_id, job_analysis_case_id, job_profile_id,
    analysis_version_code, analysis_method_code, analyst_reference,
    effective_from, effective_to, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000215',
    '20000000-0000-7000-8000-000000000202',
    'analysis_v2',
    'functional_job_analysis',
    'analyst:job_architecture_001',
    DATE '2026-08-01',
    NULL,
    TIMESTAMPTZ '2026-08-18 00:11:00+00'
);
INSERT INTO job_analysis_source_link (
    tenant_record_id, job_analysis_source_link_id, job_analysis_case_id,
    source_version_id, evidence_role_code, source_span_reference, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000216',
    '20000000-0000-7000-8000-000000000215',
    '20000000-0000-7000-8000-000000000204',
    'task_basis',
    'section:job-analysis-overview',
    TIMESTAMPTZ '2026-08-18 00:12:00+00'
);
INSERT INTO task_statement (
    tenant_record_id, task_statement_id, job_analysis_case_id,
    task_sequence_number, task_text, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000217',
    '20000000-0000-7000-8000-000000000215',
    1,
    'Incomplete task without linked FJA or KSAO evidence.',
    TIMESTAMPTZ '2026-08-18 00:13:00+00'
);
SQL

set +e
incomplete_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO job_analysis_approval_record (
    tenant_record_id, job_analysis_approval_record_id, job_analysis_case_id,
    approver_reference, approval_reason, evidence_version_code, approved_at
) VALUES (
    '20000000-0000-7000-8000-000000000201',
    '20000000-0000-7000-8000-000000000218',
    '20000000-0000-7000-8000-000000000215',
    'sme_panel:job_architecture_review_002',
    'Incomplete evidence must be rejected.',
    'approval_v1',
    TIMESTAMPTZ '2026-08-18 00:14:00+00'
);
SQL
} 2>&1)"
incomplete_status=$?
set -e
if [[ ${incomplete_status} -eq 0 ]]; then
    echo "job analysis approval accepted an unlinked task" >&2
    exit 1
fi
if [[ "${incomplete_output}" != *"job analysis approval requires every task to link FJA and KSAO evidence"* ]]; then
    echo "incomplete job analysis failed for an unexpected reason: ${incomplete_output}" >&2
    exit 1
fi

# Tenant-qualified foreign keys must reject a source version from another
# tenant even when all UUIDs are individually valid.
set +e
cross_tenant_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO job_analysis_source_link (
    tenant_record_id, job_analysis_source_link_id, job_analysis_case_id,
    source_version_id, evidence_role_code, source_span_reference, recorded_at
) VALUES (
    '20000000-0000-7000-8000-000000000301',
    '20000000-0000-7000-8000-000000000303',
    '20000000-0000-7000-8000-000000000205',
    '20000000-0000-7000-8000-000000000204',
    'task_basis',
    'section:cross-tenant',
    TIMESTAMPTZ '2026-08-18 00:15:00+00'
);
SQL
} 2>&1)"
cross_tenant_status=$?
set -e
if [[ ${cross_tenant_status} -eq 0 ]]; then
    echo "job analysis source linkage crossed a tenant boundary" >&2
    exit 1
fi

# Approved evidence is immutable under UPDATE, DELETE, and TRUNCATE.
set +e
update_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE task_statement
SET task_text = 'Mutated task text'
WHERE task_statement_id = '20000000-0000-7000-8000-000000000207';
SQL
} 2>&1)"
update_status=$?
set -e
if [[ ${update_status} -eq 0 || "${update_output}" != *"append-only relation cannot be updated or deleted"* ]]; then
    echo "job analysis task update was not rejected by the append-only boundary: ${update_output}" >&2
    exit 1
fi

set +e
truncate_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
TRUNCATE TABLE task_statement CASCADE;
SQL
} 2>&1)"
truncate_status=$?
set -e
if [[ ${truncate_status} -eq 0 || "${truncate_output}" != *"job analysis evidence cannot be truncated"* ]]; then
    echo "job analysis evidence TRUNCATE was not rejected: ${truncate_output}" >&2
    exit 1
fi

# RLS must expose only the bound tenant to a NOBYPASSRLS application role.
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'orgmetra_job_analysis_test') THEN
        CREATE ROLE orgmetra_job_analysis_test NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
    END IF;
END;
$$;
GRANT SELECT ON source_record, source_version, job_analysis_case,
    job_analysis_source_link, task_statement, task_rating, fja_function,
    task_fja_link, ksao_requirement, task_ksao_link,
    job_analysis_approval_record TO orgmetra_job_analysis_test;
SET ROLE orgmetra_job_analysis_test;
SET orgmetra.tenant_record_id = '20000000-0000-7000-8000-000000000301';
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM job_analysis_case
        WHERE job_analysis_case_id = '20000000-0000-7000-8000-000000000205'
    ) THEN
        RAISE EXCEPTION 'foreign tenant can see job analysis case';
    END IF;
END;
$$;
RESET ROLE;
SQL
