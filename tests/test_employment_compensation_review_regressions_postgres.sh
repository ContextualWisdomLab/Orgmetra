#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

relation_present="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc \
    "SELECT pg_catalog.to_regclass('public.employment_base_compensation_record') IS NOT NULL;")"
if [[ "${relation_present}" != "t" ]]; then
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0018_employment_compensation_core.sql
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('30000000-0000-7000-8000-000000000001', 'tenant_review_regression');

INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES (
    '30000000-0000-7000-8000-000000000001',
    '30000000-0000-7000-8000-000000000101'
);

INSERT INTO employment_record (
    tenant_record_id,
    employment_record_id,
    person_record_id,
    recorded_from
) VALUES
    (
        '30000000-0000-7000-8000-000000000001',
        '30000000-0000-7000-8000-000000000201',
        '30000000-0000-7000-8000-000000000101',
        TIMESTAMPTZ '2026-01-01 00:00:00+00'
    ),
    (
        '30000000-0000-7000-8000-000000000001',
        '30000000-0000-7000-8000-000000000202',
        '30000000-0000-7000-8000-000000000101',
        TIMESTAMPTZ '2026-01-01 00:00:00+00'
    );
SQL

expect_failure() {
    local label="$1"
    local expected="$2"
    local sql="$3"
    local output
    local status

    set +e
    output="$(printf '%s\n' "${sql}" | psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 2>&1)"
    status=$?
    set -e

    if [[ ${status} -eq 0 ]]; then
        echo "${label} unexpectedly succeeded" >&2
        exit 1
    fi
    if [[ "${output}" != *"${expected}"* ]]; then
        echo "${label} failed for an unexpected reason: ${output}" >&2
        exit 1
    fi
}

expect_failure \
    "Nil compensation anchor identity" \
    "employment_base_compensation_record_id_operational_check" \
    "INSERT INTO employment_base_compensation_record (tenant_record_id, employment_base_compensation_record_id, employment_record_id) VALUES ('30000000-0000-7000-8000-000000000001', '00000000-0000-0000-0000-000000000000', '30000000-0000-7000-8000-000000000202');"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO employment_base_compensation_record (
    tenant_record_id,
    employment_base_compensation_record_id,
    employment_record_id
) VALUES (
    '30000000-0000-7000-8000-000000000001',
    '30000000-0000-7000-8000-000000000301',
    '30000000-0000-7000-8000-000000000201'
);
SQL

expect_failure \
    "Max compensation version identity" \
    "employment_base_compensation_version_id_operational_check" \
    "INSERT INTO employment_base_compensation_version (tenant_record_id, employment_base_compensation_version_id, employment_base_compensation_record_id, base_compensation_amount, currency_code, pay_rate_period_code, effective_from) VALUES ('30000000-0000-7000-8000-000000000001', 'ffffffff-ffff-ffff-ffff-ffffffffffff', '30000000-0000-7000-8000-000000000301', 1.0000, 'USD', 'year', DATE '2026-01-01');"

expect_failure \
    "NaN base compensation" \
    "employment_base_compensation_amount_check" \
    "INSERT INTO employment_base_compensation_version (tenant_record_id, employment_base_compensation_version_id, employment_base_compensation_record_id, base_compensation_amount, currency_code, pay_rate_period_code, effective_from) VALUES ('30000000-0000-7000-8000-000000000001', '30000000-0000-7000-8000-000000000402', '30000000-0000-7000-8000-000000000301', 'NaN'::numeric, 'USD', 'year', DATE '2026-01-01');"

expect_failure \
    "Infinite base compensation" \
    "employment_base_compensation_amount_check" \
    "INSERT INTO employment_base_compensation_version (tenant_record_id, employment_base_compensation_version_id, employment_base_compensation_record_id, base_compensation_amount, currency_code, pay_rate_period_code, effective_from) VALUES ('30000000-0000-7000-8000-000000000001', '30000000-0000-7000-8000-000000000409', '30000000-0000-7000-8000-000000000301', 'Infinity'::numeric, 'USD', 'year', DATE '2026-01-01');"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO employment_base_compensation_version (
    tenant_record_id,
    employment_base_compensation_version_id,
    employment_base_compensation_record_id,
    base_compensation_amount,
    currency_code,
    pay_rate_period_code,
    effective_from
) VALUES (
    '30000000-0000-7000-8000-000000000001',
    '30000000-0000-7000-8000-000000000401',
    '30000000-0000-7000-8000-000000000301',
    100000.0000,
    'USD',
    'year',
    DATE '2026-01-01'
);
SQL

expect_failure \
    "anchor closure with an open compensation version" \
    "cannot close base-compensation anchor while a recorded version remains open" \
    "BEGIN; UPDATE employment_base_compensation_record SET recorded_to = pg_catalog.transaction_timestamp() WHERE employment_base_compensation_record_id = '30000000-0000-7000-8000-000000000301'; SET CONSTRAINTS ALL IMMEDIATE; COMMIT;"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
UPDATE employment_base_compensation_version
SET recorded_to = pg_catalog.transaction_timestamp()
WHERE employment_base_compensation_version_id = '30000000-0000-7000-8000-000000000401';
UPDATE employment_base_compensation_record
SET recorded_to = pg_catalog.transaction_timestamp()
WHERE employment_base_compensation_record_id = '30000000-0000-7000-8000-000000000301';
SET CONSTRAINTS ALL IMMEDIATE;
COMMIT;
SQL

expect_failure \
    "version insert against a closed compensation anchor" \
    "base-compensation version requires an open compensation anchor" \
    "INSERT INTO employment_base_compensation_version (tenant_record_id, employment_base_compensation_version_id, employment_base_compensation_record_id, base_compensation_amount, currency_code, pay_rate_period_code, effective_from) VALUES ('30000000-0000-7000-8000-000000000001', '30000000-0000-7000-8000-000000000403', '30000000-0000-7000-8000-000000000301', 101000.0000, 'USD', 'year', DATE '2027-01-01');"

expect_failure \
    "compensation version TRUNCATE" \
    "employment base-compensation history cannot be truncated" \
    "TRUNCATE TABLE employment_base_compensation_version;"

expect_failure \
    "compensation anchor TRUNCATE CASCADE" \
    "employment base-compensation history cannot be truncated" \
    "TRUNCATE TABLE employment_base_compensation_record CASCADE;"

echo "employment compensation review regressions passed"
