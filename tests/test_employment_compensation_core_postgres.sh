#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
if [[ -f database/migrations/0018_employment_compensation_core.sql ]]; then
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0018_employment_compensation_core.sql
fi

relation_present="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc \
    "SELECT pg_catalog.to_regclass('public.employment_base_compensation_record') IS NOT NULL;")"
if [[ "${relation_present}" != "t" ]]; then
    echo "employment-scoped base-compensation relation is missing" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES
    ('10000000-0000-7000-8000-000000000001', 'tenant_alpha'),
    ('20000000-0000-7000-8000-000000000001', 'tenant_beta');

INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES
    ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000101'),
    ('20000000-0000-7000-8000-000000000001', '20000000-0000-7000-8000-000000000101');

INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id, recorded_from
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000201',
        '10000000-0000-7000-8000-000000000101',
        TIMESTAMPTZ '2026-01-01 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000202',
        '10000000-0000-7000-8000-000000000101',
        TIMESTAMPTZ '2026-01-01 00:00:00+00'
    ),
    (
        '20000000-0000-7000-8000-000000000001',
        '20000000-0000-7000-8000-000000000201',
        '20000000-0000-7000-8000-000000000101',
        TIMESTAMPTZ '2026-01-01 00:00:00+00'
    );

INSERT INTO employment_base_compensation_record (
    tenant_record_id, employment_base_compensation_record_id, employment_record_id
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000301',
        '10000000-0000-7000-8000-000000000201'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000302',
        '10000000-0000-7000-8000-000000000202'
    );

INSERT INTO employment_base_compensation_version (
    tenant_record_id, employment_base_compensation_version_id,
    employment_base_compensation_record_id, base_compensation_amount,
    currency_code, pay_rate_period_code, effective_from
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000401',
        '10000000-0000-7000-8000-000000000301',
        120000.0000, 'USD', 'year', DATE '2026-01-01'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '10000000-0000-7000-8000-000000000402',
        '10000000-0000-7000-8000-000000000302',
        80.0000, 'USD', 'hour', DATE '2026-01-01'
    );
SQL

concurrent_compensation_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM employment_base_compensation_record AS compensation
JOIN employment_base_compensation_version AS version
  ON version.tenant_record_id = compensation.tenant_record_id
 AND version.employment_base_compensation_record_id = compensation.employment_base_compensation_record_id
WHERE compensation.tenant_record_id = '10000000-0000-7000-8000-000000000001'
  AND compensation.employment_record_id IN (
      '10000000-0000-7000-8000-000000000201',
      '10000000-0000-7000-8000-000000000202'
  )
  AND version.recorded_to IS NULL;
")"
if [[ "${concurrent_compensation_count}" != "2" ]]; then
    echo "concurrent employments did not retain independent base-compensation facts" >&2
    exit 1
fi

set +e
legacy_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO compensation_record (
    tenant_record_id, compensation_record_id, person_record_id, amount_value,
    currency_code, effective_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '10000000-0000-7000-8000-000000000501',
    '10000000-0000-7000-8000-000000000101',
    90000, 'USD', DATE '2026-01-01'
);
SQL
} 2>&1)"
legacy_status=$?
set -e
if [[ ${legacy_status} -eq 0 ]]; then
    echo "legacy person-scoped compensation accepted a new ambiguous write" >&2
    exit 1
fi
if [[ "${legacy_output}" != *"legacy compensation_record is read-only for new writes"* ]]; then
    echo "legacy compensation write failed for an unexpected reason: ${legacy_output}" >&2
    exit 1
fi

set +e
duplicate_anchor_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO employment_base_compensation_record (
    tenant_record_id, employment_base_compensation_record_id, employment_record_id
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '10000000-0000-7000-8000-000000000303',
    '10000000-0000-7000-8000-000000000201'
);
SQL
} 2>&1)"
duplicate_anchor_status=$?
set -e
if [[ ${duplicate_anchor_status} -eq 0 ]]; then
    echo "one employment accepted multiple base-compensation anchors" >&2
    exit 1
fi
if [[ "${duplicate_anchor_output}" != *"employment_base_compensation_employment_unique"* ]]; then
    echo "duplicate compensation anchor failed for an unexpected reason: ${duplicate_anchor_output}" >&2
    exit 1
fi

set +e
backdated_recorded_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO employment_base_compensation_record (
    tenant_record_id, employment_base_compensation_record_id, employment_record_id,
    recorded_from
) VALUES (
    '20000000-0000-7000-8000-000000000001',
    '20000000-0000-7000-8000-000000000301',
    '20000000-0000-7000-8000-000000000201',
    TIMESTAMPTZ '2020-01-01 00:00:00+00'
);
SQL
} 2>&1)"
backdated_recorded_status=$?
set -e
if [[ ${backdated_recorded_status} -eq 0 ]]; then
    echo "base compensation accepted caller-authored system-recorded time" >&2
    exit 1
fi
if [[ "${backdated_recorded_output}" != *"base-compensation recorded_from must equal the current transaction timestamp"* ]]; then
    echo "backdated compensation system time failed for an unexpected reason: ${backdated_recorded_output}" >&2
    exit 1
fi

set +e
cross_tenant_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO employment_base_compensation_record (
    tenant_record_id, employment_base_compensation_record_id, employment_record_id
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '10000000-0000-7000-8000-000000000304',
    '20000000-0000-7000-8000-000000000201'
);
SQL
} 2>&1)"
cross_tenant_status=$?
set -e
if [[ ${cross_tenant_status} -eq 0 ]]; then
    echo "base compensation accepted an employment owned by another tenant" >&2
    exit 1
fi
if [[ "${cross_tenant_output}" != *"employment_base_compensation_employment_tenant_fk"* ]]; then
    echo "cross-tenant compensation write failed for an unexpected reason: ${cross_tenant_output}" >&2
    exit 1
fi

expect_version_failure() {
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

expect_version_failure \
    "negative base compensation" \
    "employment_base_compensation_amount_check" \
    "INSERT INTO employment_base_compensation_version (tenant_record_id, employment_base_compensation_version_id, employment_base_compensation_record_id, base_compensation_amount, currency_code, pay_rate_period_code, effective_from) VALUES ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000403', '10000000-0000-7000-8000-000000000301', -1.0000, 'USD', 'year', DATE '2027-01-01');"

expect_version_failure \
    "lowercase currency" \
    "employment_base_compensation_currency_check" \
    "INSERT INTO employment_base_compensation_version (tenant_record_id, employment_base_compensation_version_id, employment_base_compensation_record_id, base_compensation_amount, currency_code, pay_rate_period_code, effective_from) VALUES ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000404', '10000000-0000-7000-8000-000000000301', 1.0000, 'usd', 'year', DATE '2027-01-01');"

expect_version_failure \
    "unsupported pay-rate period" \
    "employment_base_compensation_rate_period_check" \
    "INSERT INTO employment_base_compensation_version (tenant_record_id, employment_base_compensation_version_id, employment_base_compensation_record_id, base_compensation_amount, currency_code, pay_rate_period_code, effective_from) VALUES ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000405', '10000000-0000-7000-8000-000000000301', 1.0000, 'USD', 'annual', DATE '2027-01-01');"

expect_version_failure \
    "backdated compensation version system time" \
    "base-compensation recorded_from must equal the current transaction timestamp" \
    "INSERT INTO employment_base_compensation_version (tenant_record_id, employment_base_compensation_version_id, employment_base_compensation_record_id, base_compensation_amount, currency_code, pay_rate_period_code, effective_from, effective_to, recorded_from) VALUES ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000406', '10000000-0000-7000-8000-000000000301', 100000.0000, 'USD', 'year', DATE '2025-01-01', DATE '2025-12-31', TIMESTAMPTZ '2020-01-01 00:00:00+00');"

expect_version_failure \
    "overlapping compensation truth" \
    "employment_base_compensation_bitemporal_exclusion" \
    "INSERT INTO employment_base_compensation_version (tenant_record_id, employment_base_compensation_version_id, employment_base_compensation_record_id, base_compensation_amount, currency_code, pay_rate_period_code, effective_from) VALUES ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000407', '10000000-0000-7000-8000-000000000301', 130000.0000, 'USD', 'year', DATE '2026-06-01');"

set +e
rewrite_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE employment_base_compensation_version
SET base_compensation_amount = 125000.0000
WHERE employment_base_compensation_version_id = '10000000-0000-7000-8000-000000000401';
SQL
} 2>&1)"
rewrite_status=$?
set -e
if [[ ${rewrite_status} -eq 0 ]]; then
    echo "base-compensation history allowed in-place business mutation" >&2
    exit 1
fi
if [[ "${rewrite_output}" != *"bitemporal correction may only close an open recorded interval"* ]]; then
    echo "base-compensation rewrite failed for an unexpected reason: ${rewrite_output}" >&2
    exit 1
fi

set +e
caller_close_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE employment_base_compensation_version
SET recorded_to = TIMESTAMPTZ '2026-12-31 23:59:59+00'
WHERE employment_base_compensation_version_id = '10000000-0000-7000-8000-000000000401';
SQL
} 2>&1)"
caller_close_status=$?
set -e
if [[ ${caller_close_status} -eq 0 ]]; then
    echo "base compensation accepted caller-authored recorded_to system time" >&2
    exit 1
fi
if [[ "${caller_close_output}" != *"base-compensation recorded_to must equal the current transaction timestamp"* ]]; then
    echo "caller-authored compensation recorded_to failed for an unexpected reason: ${caller_close_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE employment_base_compensation_version
SET recorded_to = pg_catalog.transaction_timestamp()
WHERE employment_base_compensation_version_id = '10000000-0000-7000-8000-000000000401';
SQL

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE orgmetra_compensation_reader NOLOGIN NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO orgmetra_compensation_reader;
GRANT SELECT ON employment_base_compensation_record TO orgmetra_compensation_reader;
GRANT SELECT ON employment_base_compensation_version TO orgmetra_compensation_reader;
SQL

missing_context_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SET ROLE orgmetra_compensation_reader;
SELECT count(*) FROM employment_base_compensation_record;
")"
if [[ "${missing_context_count}" != "0" ]]; then
    echo "compensation reader saw tenant rows without tenant context" >&2
    exit 1
fi

alpha_context_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SET ROLE orgmetra_compensation_reader;
SET orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
SELECT count(*) FROM employment_base_compensation_record;
")"
if [[ "${alpha_context_count}" != "2" ]]; then
    echo "tenant-alpha reader did not see exactly its two compensation anchors" >&2
    exit 1
fi

beta_context_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SET ROLE orgmetra_compensation_reader;
SET orgmetra.tenant_record_id = '20000000-0000-7000-8000-000000000001';
SELECT count(*) FROM employment_base_compensation_record;
")"
if [[ "${beta_context_count}" != "0" ]]; then
    echo "tenant-beta reader saw tenant-alpha compensation anchors" >&2
    exit 1
fi

echo "employment-scoped base-compensation contract passed"