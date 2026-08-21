#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

# Apply the complete protected-schema migration sequence. On the RED commit this
# intentionally leaves candidate_application_record absent; the assertions below
# define the normalized recruiting contract that the repair must satisfy.
for migration in database/migrations/*.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ALPHA="10000000-0000-7000-8000-000000000001"
TENANT_BETA="20000000-0000-7000-8000-000000000001"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES
    ('10000000-0000-7000-8000-000000000001', 'tenant_alpha'),
    ('20000000-0000-7000-8000-000000000001', 'tenant_beta');

INSERT INTO candidate_profile (
    tenant_record_id, candidate_profile_id, application_status_code, recorded_from
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000011',
        'legacy_unscoped',
        TIMESTAMPTZ '2026-08-21 09:00:00+00'
    ),
    (
        '20000000-0000-7000-8000-000000000001',
        '20000000-0000-7000-8000-000000000011',
        'legacy_unscoped',
        TIMESTAMPTZ '2026-08-21 09:00:00+00'
    );

INSERT INTO job_profile (
    tenant_record_id, job_profile_id, recorded_from
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000021',
        TIMESTAMPTZ '2026-08-21 09:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000022',
        TIMESTAMPTZ '2026-08-21 09:00:00+00'
    ),
    (
        '20000000-0000-7000-8000-000000000001',
        '20000000-0000-7000-8000-000000000021',
        TIMESTAMPTZ '2026-08-21 09:00:00+00'
    );

INSERT INTO organization_unit (
    tenant_record_id, organization_unit_id, recorded_from
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000031',
        TIMESTAMPTZ '2026-08-21 09:00:00+00'
    ),
    (
        '20000000-0000-7000-8000-000000000001',
        '20000000-0000-7000-8000-000000000031',
        TIMESTAMPTZ '2026-08-21 09:00:00+00'
    );

INSERT INTO position_record (
    tenant_record_id, position_record_id, organization_unit_id, job_profile_id, recorded_from
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000041',
        '10000000-0000-7000-8000-000000000031',
        '10000000-0000-7000-8000-000000000021',
        TIMESTAMPTZ '2026-08-21 09:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000042',
        '10000000-0000-7000-8000-000000000031',
        '10000000-0000-7000-8000-000000000022',
        TIMESTAMPTZ '2026-08-21 09:00:00+00'
    );
SQL

# One candidate can hold independent application identities for different
# requisition/job/seat contexts. Application workflow state must not live on
# candidate_profile, where it would collapse these concurrent applications.
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_application_record (
    tenant_record_id, candidate_application_record_id, candidate_profile_id,
    job_profile_id, position_record_id, requisition_reference, submitted_at,
    recorded_from
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000051',
        '10000000-0000-7000-8000-000000000011',
        '10000000-0000-7000-8000-000000000021',
        '10000000-0000-7000-8000-000000000041',
        'requisition:11111111-1111-4111-8111-111111111111',
        TIMESTAMPTZ '2026-08-21 09:10:00+00',
        TIMESTAMPTZ '2026-08-21 09:10:01+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000052',
        '10000000-0000-7000-8000-000000000011',
        '10000000-0000-7000-8000-000000000022',
        '10000000-0000-7000-8000-000000000042',
        'requisition:22222222-2222-4222-8222-222222222222',
        TIMESTAMPTZ '2026-08-21 09:11:00+00',
        TIMESTAMPTZ '2026-08-21 09:11:01+00'
    );
SQL

application_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM candidate_application_record
WHERE tenant_record_id = '${TENANT_ALPHA}'::uuid
  AND candidate_profile_id = '10000000-0000-7000-8000-000000000011'::uuid
  AND recorded_to IS NULL;
")"
if [[ "${application_count}" != "2" ]]; then
    echo "one candidate did not retain two independent application identities" >&2
    exit 1
fi

set +e
cross_tenant_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_application_record (
    tenant_record_id, candidate_application_record_id, candidate_profile_id,
    job_profile_id, requisition_reference, submitted_at, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '10000000-0000-7000-8000-000000000053',
    '20000000-0000-7000-8000-000000000011',
    '10000000-0000-7000-8000-000000000021',
    'requisition:33333333-3333-4333-8333-333333333333',
    TIMESTAMPTZ '2026-08-21 09:12:00+00',
    TIMESTAMPTZ '2026-08-21 09:12:01+00'
);
SQL
} 2>&1)"
cross_tenant_status=$?
set -e
if [[ ${cross_tenant_status} -eq 0 ]]; then
    echo "candidate application accepted a candidate owned by another tenant" >&2
    exit 1
fi
if [[ "${cross_tenant_output}" != *"candidate_application_candidate_tenant_fk"* ]]; then
    echo "cross-tenant candidate failed for an unexpected reason: ${cross_tenant_output}" >&2
    exit 1
fi

set +e
position_job_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_application_record (
    tenant_record_id, candidate_application_record_id, candidate_profile_id,
    job_profile_id, position_record_id, requisition_reference, submitted_at,
    recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '10000000-0000-7000-8000-000000000054',
    '10000000-0000-7000-8000-000000000011',
    '10000000-0000-7000-8000-000000000021',
    '10000000-0000-7000-8000-000000000042',
    'requisition:44444444-4444-4444-8444-444444444444',
    TIMESTAMPTZ '2026-08-21 09:13:00+00',
    TIMESTAMPTZ '2026-08-21 09:13:01+00'
);
SQL
} 2>&1)"
position_job_status=$?
set -e
if [[ ${position_job_status} -eq 0 ]]; then
    echo "candidate application accepted a Position belonging to another Job" >&2
    exit 1
fi
if [[ "${position_job_output}" != *"candidate_application_position_job_tenant_fk"* ]]; then
    echo "Position/Job mismatch failed for an unexpected reason: ${position_job_output}" >&2
    exit 1
fi

set +e
duplicate_requisition_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_application_record (
    tenant_record_id, candidate_application_record_id, candidate_profile_id,
    job_profile_id, requisition_reference, submitted_at, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '10000000-0000-7000-8000-000000000055',
    '10000000-0000-7000-8000-000000000011',
    '10000000-0000-7000-8000-000000000021',
    'requisition:11111111-1111-4111-8111-111111111111',
    TIMESTAMPTZ '2026-08-21 09:14:00+00',
    TIMESTAMPTZ '2026-08-21 09:14:01+00'
);
SQL
} 2>&1)"
duplicate_requisition_status=$?
set -e
if [[ ${duplicate_requisition_status} -eq 0 ]]; then
    echo "candidate application duplicated the same candidate/requisition identity" >&2
    exit 1
fi
if [[ "${duplicate_requisition_output}" != *"candidate_application_candidate_requisition_unique"* ]]; then
    echo "duplicate candidate/requisition failed unexpectedly: ${duplicate_requisition_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_application_stage_record (
    tenant_record_id, candidate_application_stage_record_id,
    candidate_application_record_id, application_stage_code,
    effective_from, effective_to, recorded_from
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000061',
        '10000000-0000-7000-8000-000000000051',
        'received',
        TIMESTAMPTZ '2026-08-21 09:10:00+00',
        TIMESTAMPTZ '2026-08-21 10:00:00+00',
        TIMESTAMPTZ '2026-08-21 09:10:01+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000062',
        '10000000-0000-7000-8000-000000000051',
        'screening',
        TIMESTAMPTZ '2026-08-21 10:00:00+00',
        NULL,
        TIMESTAMPTZ '2026-08-21 10:00:01+00'
    );
SQL

set +e
overlap_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_application_stage_record (
    tenant_record_id, candidate_application_stage_record_id,
    candidate_application_record_id, application_stage_code,
    effective_from, effective_to, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '10000000-0000-7000-8000-000000000063',
    '10000000-0000-7000-8000-000000000051',
    'assessment',
    TIMESTAMPTZ '2026-08-21 09:30:00+00',
    TIMESTAMPTZ '2026-08-21 10:30:00+00',
    TIMESTAMPTZ '2026-08-21 11:00:00+00'
);
SQL
} 2>&1)"
overlap_status=$?
set -e
if [[ ${overlap_status} -eq 0 ]]; then
    echo "candidate application accepted contradictory bitemporal stage history" >&2
    exit 1
fi
if [[ "${overlap_output}" != *"candidate_application_stage_bitemporal_exclusion"* ]]; then
    echo "overlapping stage failed for an unexpected reason: ${overlap_output}" >&2
    exit 1
fi

set +e
final_outcome_stage_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_application_stage_record (
    tenant_record_id, candidate_application_stage_record_id,
    candidate_application_record_id, application_stage_code,
    effective_from, effective_to, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '10000000-0000-7000-8000-000000000064',
    '10000000-0000-7000-8000-000000000052',
    'hired',
    TIMESTAMPTZ '2026-08-21 11:00:00+00',
    NULL,
    TIMESTAMPTZ '2026-08-21 11:00:01+00'
);
SQL
} 2>&1)"
final_outcome_stage_status=$?
set -e
if [[ ${final_outcome_stage_status} -eq 0 ]]; then
    echo "workflow stage encoded a high-impact hire outcome outside selection_decision" >&2
    exit 1
fi
if [[ "${final_outcome_stage_output}" != *"candidate_application_stage_code_check"* ]]; then
    echo "final outcome stage failed for an unexpected reason: ${final_outcome_stage_output}" >&2
    exit 1
fi

set +e
rewrite_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE candidate_application_stage_record
SET application_stage_code = 'assessment'
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'
  AND candidate_application_stage_record_id = '10000000-0000-7000-8000-000000000061';
SQL
} 2>&1)"
rewrite_status=$?
set -e
if [[ ${rewrite_status} -eq 0 ]]; then
    echo "candidate application stage history was rewritten in place" >&2
    exit 1
fi
if [[ "${rewrite_output}" != *"bitemporal correction may only close an open recorded interval"* ]]; then
    echo "stage rewrite failed for an unexpected reason: ${rewrite_output}" >&2
    exit 1
fi

# A correction closes the prior system-recorded interval and appends replacement
# knowledge for the same business-time slice.
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE candidate_application_stage_record
SET recorded_to = TIMESTAMPTZ '2026-08-21 12:00:00+00'
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'
  AND candidate_application_stage_record_id = '10000000-0000-7000-8000-000000000061';

INSERT INTO candidate_application_stage_record (
    tenant_record_id, candidate_application_stage_record_id,
    candidate_application_record_id, application_stage_code,
    effective_from, effective_to, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '10000000-0000-7000-8000-000000000065',
    '10000000-0000-7000-8000-000000000051',
    'screening',
    TIMESTAMPTZ '2026-08-21 09:10:00+00',
    TIMESTAMPTZ '2026-08-21 10:00:00+00',
    TIMESTAMPTZ '2026-08-21 12:00:00+00'
);
SQL

rls_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_class
WHERE relnamespace = 'public'::regnamespace
  AND relname IN ('candidate_application_record', 'candidate_application_stage_record')
  AND relrowsecurity
  AND relforcerowsecurity;
")"
if [[ "${rls_count}" != "2" ]]; then
    echo "candidate application relations do not both force row-level security" >&2
    exit 1
fi

set +e
truncate_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
    'TRUNCATE TABLE candidate_application_stage_record;' ; } 2>&1)"
truncate_status=$?
set -e
if [[ ${truncate_status} -eq 0 ]]; then
    echo "candidate application stage history was truncatable" >&2
    exit 1
fi
if [[ "${truncate_output}" != *"candidate application history cannot be truncated"* ]]; then
    echo "candidate application TRUNCATE failed for an unexpected reason: ${truncate_output}" >&2
    exit 1
fi

# The beta tenant remains present to prove tenant-qualified identities were not
# accidentally collapsed while exercising cross-tenant referential failures.
beta_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*) FROM tenant_record WHERE tenant_record_id = '${TENANT_BETA}'::uuid;
")"
if [[ "${beta_count}" != "1" ]]; then
    echo "cross-tenant regression fixture lost the beta tenant" >&2
    exit 1
fi

echo "candidate application PostgreSQL contract passed"
