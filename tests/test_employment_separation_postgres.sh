#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
TENANT_ID='10000000-0000-7000-8000-000000000001'
FOREIGN_TENANT_ID='20000000-0000-7000-8000-000000000001'
PERSON_ID='00000000-0000-7000-8000-000000000001'

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
    database/migrations/0010_validity_study_case_integrity.sql \
    database/migrations/0011_criterion_observation_scope.sql \
    database/migrations/0012_people_mutation_idempotency.sql \
    database/migrations/0013_job_analysis_snapshot.sql \
    database/migrations/0014_employment_separation_transition.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES
    ('10000000-0000-7000-8000-000000000001', 'tenant_alpha'),
    ('20000000-0000-7000-8000-000000000001', 'tenant_beta');

INSERT INTO person_record (tenant_record_id, person_record_id, recorded_from)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000001',
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);

INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id, recorded_from
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000101',
        '00000000-0000-7000-8000-000000000001',
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000102',
        '00000000-0000-7000-8000-000000000001',
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000103',
        '00000000-0000-7000-8000-000000000001',
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000104',
        '00000000-0000-7000-8000-000000000001',
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    );

INSERT INTO employment_record_version (
    tenant_record_id,
    employment_record_version_id,
    employment_record_id,
    employment_status_code,
    employment_concurrency_code,
    effective_from,
    effective_to,
    recorded_from
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000201',
        '00000000-0000-7000-8000-000000000101',
        'active', 'exclusive', DATE '2026-01-01', NULL,
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000202',
        '00000000-0000-7000-8000-000000000102',
        'active', 'concurrent', DATE '2026-01-01', NULL,
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000203',
        '00000000-0000-7000-8000-000000000103',
        'active', 'concurrent', DATE '2026-01-01', DATE '2026-09-01',
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000204',
        '00000000-0000-7000-8000-000000000103',
        'leave', 'concurrent', DATE '2026-09-01', NULL,
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000205',
        '00000000-0000-7000-8000-000000000104',
        'active', 'concurrent', DATE '2026-01-01', NULL,
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    );

INSERT INTO organization_unit (tenant_record_id, organization_unit_id, recorded_from)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000301',
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
INSERT INTO job_profile (tenant_record_id, job_profile_id, recorded_from)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000302',
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
INSERT INTO position_record (
    tenant_record_id, position_record_id, organization_unit_id, job_profile_id, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000303',
    '00000000-0000-7000-8000-000000000303',
    '00000000-0000-7000-8000-000000000301',
    '00000000-0000-7000-8000-000000000302',
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
SQL
