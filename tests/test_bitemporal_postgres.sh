#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
TENANT_ID='10000000-0000-7000-8000-000000000001'

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('10000000-0000-7000-8000-000000000001', 'tenant_alpha');
INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000001'
);
INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000002',
    '00000000-0000-7000-8000-000000000001'
);
INSERT INTO employment_record_version (
    tenant_record_id, employment_record_version_id, employment_record_id,
    employment_status_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000021',
    '00000000-0000-7000-8000-000000000002',
    'active', DATE '2026-01-01', TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
INSERT INTO organization_unit (tenant_record_id, organization_unit_id)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000006'
);
INSERT INTO job_profile (tenant_record_id, job_profile_id)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000007'
);
SQL

PGAPPNAME=orgmetra_bitemporal_writer psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL' &
BEGIN;
INSERT INTO organization_unit_version (
    tenant_record_id, organization_unit_version_id, organization_unit_id, unit_name,
    organization_type_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000013',
    '00000000-0000-7000-8000-000000000006',
    'People', 'department', DATE '2026-01-01',
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
SELECT pg_sleep(2);
COMMIT;
SQL
writer_pid=$!

writer_ready=false
for _ in $(seq 1 80); do
    writer_state="$(psql "${DATABASE_URL}" -Atqc "
        SELECT count(*)
        FROM pg_stat_activity
        WHERE application_name = 'orgmetra_bitemporal_writer'
          AND wait_event = 'PgSleep';
    ")"
    if [[ "${writer_state}" == "1" ]]; then
        writer_ready=true
        break
    fi
    sleep 0.05
done
if [[ "${writer_ready}" != "true" ]]; then
    set +e
    wait "${writer_pid}"
    writer_status=$?
    set -e
    echo "concurrent writer never became observable; exit_status=${writer_status}" >&2
    exit 1
fi

set +e
conflict_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
SET statement_timeout = '5s';
INSERT INTO organization_unit_version (
    tenant_record_id, organization_unit_version_id, organization_unit_id, unit_name,
    organization_type_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000014',
    '00000000-0000-7000-8000-000000000006',
    'People and Culture', 'department', DATE '2026-01-01',
    TIMESTAMPTZ '2026-01-03 00:00:00+00'
);
SQL
} 2>&1)"
conflict_status=$?
wait "${writer_pid}"
writer_status=$?
set -e

if [[ ${writer_status} -ne 0 ]]; then
    echo "concurrent fixture writer failed unexpectedly with status ${writer_status}" >&2
    exit 1
fi
if [[ ${conflict_status} -eq 0 ]]; then
    echo "overlapping concurrent bitemporal version unexpectedly succeeded" >&2
    exit 1
fi
if [[ "${conflict_output}" != *"organization_unit_bitemporal_exclusion"* ]]; then
    echo "concurrent conflict failed for an unexpected reason: ${conflict_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
UPDATE organization_unit_version
SET recorded_to = TIMESTAMPTZ '2026-02-01 00:00:00+00'
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'
  AND organization_unit_version_id = '00000000-0000-7000-8000-000000000013';
INSERT INTO organization_unit_version (
    tenant_record_id, organization_unit_version_id, organization_unit_id, unit_name,
    organization_type_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000015',
    '00000000-0000-7000-8000-000000000006',
    'People and Culture', 'department', DATE '2026-01-01',
    TIMESTAMPTZ '2026-02-01 00:00:00+00'
);
COMMIT;
SQL

visible_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*) FROM organization_unit_version
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND organization_unit_id = '00000000-0000-7000-8000-000000000006'
  AND daterange(effective_from, effective_to, '[)') @> DATE '2026-01-15'
  AND tstzrange(recorded_from, recorded_to, '[)') @> TIMESTAMPTZ '2026-02-02 00:00:00+00';
")"
if [[ "${visible_count}" != "1" ]]; then
    echo "expected one organization version at one effective/knowledge coordinate, got ${visible_count}" >&2
    exit 1
fi

set +e
mutation_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
UPDATE organization_unit_version SET unit_name = 'Silent rewrite'
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND organization_unit_version_id = '00000000-0000-7000-8000-000000000015';
"; } 2>&1)"
mutation_status=$?
set -e
if [[ ${mutation_status} -eq 0 ]]; then
    echo "in-place bitemporal business mutation unexpectedly succeeded" >&2
    exit 1
fi
if [[ "${mutation_output}" != *"bitemporal correction may only close an open recorded interval"* ]]; then
    echo "business mutation failed for an unexpected reason: ${mutation_output}" >&2
    exit 1
fi

set +e
employment_mutation_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
UPDATE employment_record_version SET employment_status_code = 'terminated'
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND employment_record_version_id = '00000000-0000-7000-8000-000000000021';
"; } 2>&1)"
employment_mutation_status=$?
set -e
if [[ ${employment_mutation_status} -eq 0 ]]; then
    echo "employment bitemporal business mutation unexpectedly succeeded" >&2
    exit 1
fi
if [[ "${employment_mutation_output}" != *"bitemporal correction may only close an open recorded interval"* ]]; then
    echo "employment mutation failed for an unexpected reason: ${employment_mutation_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO person_name_record (
    tenant_record_id, person_name_record_id, person_record_id, display_name,
    effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000011',
    '00000000-0000-7000-8000-000000000001',
    'Ada Lovelace', DATE '2026-01-01', TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
INSERT INTO job_profile_version (
    tenant_record_id, job_profile_version_id, job_profile_id, job_title, job_family_code,
    job_version_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000016',
    '00000000-0000-7000-8000-000000000007',
    'Principal AI Product Architect', 'product', '2026.1', DATE '2026-01-01',
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
SQL

set +e
overlap_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO employment_record_version (
    tenant_record_id, employment_record_version_id, employment_record_id,
    employment_status_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000022',
    '00000000-0000-7000-8000-000000000002',
    'leave', DATE '2026-01-01', TIMESTAMPTZ '2026-01-03 00:00:00+00'
);
SQL
} 2>&1)"
overlap_status=$?
set -e
if [[ ${overlap_status} -eq 0 ]]; then
    echo "overlapping employment versions unexpectedly succeeded" >&2
    exit 1
fi
if [[ "${overlap_output}" != *"employment_record_bitemporal_exclusion"* ]]; then
    echo "employment overlap failed for an unexpected reason: ${overlap_output}" >&2
    exit 1
fi

history_contract_tmp="$(mktemp -d)"
trap 'rm -rf "${history_contract_tmp}"' EXIT
python - "${history_contract_tmp}" <<'PY'
import ast
from pathlib import Path
import sys

source_path = Path("services/people-api/src/orgmetra_people_api/postgres_employment_history.py")
module = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
values: dict[str, str] = {}
for node in module.body:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        continue
    target = node.targets[0]
    if not isinstance(target, ast.Name):
        continue
    value = node.value
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        values[target.id] = value.value
    elif (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Attribute)
        and value.func.attr == "strip"
        and not value.args
        and not value.keywords
        and isinstance(value.func.value, ast.Constant)
        and isinstance(value.func.value.value, str)
    ):
        values[target.id] = value.func.value.value.strip()

required = ("_READ_ONLY_SQL", "_TENANT_CONTEXT_SQL", "_EMPLOYMENT_HISTORY_SQL")
missing = [name for name in required if name not in values]
if missing:
    raise SystemExit(f"Employment-history SQL authority missing from adapter source: {missing}")

transaction_sql = values["_READ_ONLY_SQL"]
tenant_sql = values["_TENANT_CONTEXT_SQL"]
history_sql = values["_EMPLOYMENT_HISTORY_SQL"]
if transaction_sql != "SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ ONLY":
    raise SystemExit("Employment-history adapter read-only transaction contract drifted")
if tenant_sql.count("%s") != 1:
    raise SystemExit("Employment-history tenant-context placeholder contract drifted")
if history_sql.count("%s") != 6:
    raise SystemExit("Employment-history query placeholder contract drifted")

replacements = [
    ":'tenant_record_id'::uuid",
    ":'person_record_id'::uuid",
    ":'known_at'::timestamptz",
    ":'known_at'::timestamptz",
    ":'known_at'::timestamptz",
    ":'known_at'::timestamptz",
]
for replacement in replacements:
    history_sql = history_sql.replace("%s", replacement, 1)
if "%s" in history_sql:
    raise SystemExit("Employment-history query retained an unbound placeholder")

target = Path(sys.argv[1])
(target / "transaction.sql").write_text(transaction_sql + ";\n", encoding="utf-8")
(target / "tenant.sql").write_text(
    tenant_sql.replace("%s", ":'tenant_record_id'", 1) + ";\n",
    encoding="utf-8",
)
(target / "history.sql").write_text(history_sql + ";\n", encoding="utf-8")
PY

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000024',
    '00000000-0000-7000-8000-000000000001',
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
);
INSERT INTO employment_record_version (
    tenant_record_id, employment_record_version_id, employment_record_id,
    employment_status_code, employment_concurrency_code,
    effective_from, recorded_from, recorded_to
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000025',
    '00000000-0000-7000-8000-000000000024',
    'active', 'concurrent', DATE '2026-01-01',
    TIMESTAMPTZ '2026-01-02 00:00:00+00', TIMESTAMPTZ '2026-02-01 00:00:00+00'
);
INSERT INTO employment_record_version (
    tenant_record_id, employment_record_version_id, employment_record_id,
    employment_status_code, employment_concurrency_code,
    effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000026',
    '00000000-0000-7000-8000-000000000024',
    'leave', 'concurrent', DATE '2026-01-01', TIMESTAMPTZ '2026-02-01 00:00:00+00'
);
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('20000000-0000-7000-8000-000000000001', 'tenant_beta');
INSERT INTO person_record (tenant_record_id, person_record_id, recorded_from)
VALUES (
    '20000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000101',
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
);
INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id, recorded_from
) VALUES (
    '20000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000102',
    '00000000-0000-7000-8000-000000000101',
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
);
INSERT INTO employment_record_version (
    tenant_record_id, employment_record_version_id, employment_record_id,
    employment_status_code, employment_concurrency_code,
    effective_from, recorded_from
) VALUES (
    '20000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000103',
    '00000000-0000-7000-8000-000000000102',
    'active', 'exclusive', DATE '2026-01-01', TIMESTAMPTZ '2026-01-01 00:00:00+00'
);
SQL

run_employment_history_query() {
    local tenant_record_id="$1"
    local person_record_id="$2"
    local known_at="$3"
    local session_timezone="$4"
    psql "${DATABASE_URL}" -X -qAt -F '|' -v ON_ERROR_STOP=1 \
        -v tenant_record_id="${tenant_record_id}" \
        -v person_record_id="${person_record_id}" \
        -v known_at="${known_at}" <<SQL
BEGIN;
\i ${history_contract_tmp}/transaction.sql
SET TIME ZONE '${session_timezone}';
\o /dev/null
\i ${history_contract_tmp}/tenant.sql
\o
\i ${history_contract_tmp}/history.sql
ROLLBACK;
SQL
}

history_before="$(run_employment_history_query \
    '10000000-0000-7000-8000-000000000001' \
    '00000000-0000-7000-8000-000000000001' \
    '2026-01-15 00:00:00+00' \
    'Asia/Seoul')"
IFS='|' read -r history_tenant history_person history_employment history_version history_status \
    history_concurrency history_effective_from history_effective_to history_recorded_from history_recorded_to \
    <<<"${history_before}"
if [[ "${history_tenant}" != "10000000-0000-7000-8000-000000000001" \
   || "${history_person}" != "00000000-0000-7000-8000-000000000001" \
   || "${history_employment}" != "00000000-0000-7000-8000-000000000024" \
   || "${history_version}" != "00000000-0000-7000-8000-000000000025" \
   || "${history_status}" != "active" \
   || "${history_concurrency}" != "concurrent" \
   || "${history_effective_from}" != "2026-01-01" \
   || -n "${history_effective_to}" \
   || "${history_recorded_from}" != "2026-01-02 00:00:00" \
   || "${history_recorded_to}" != "2026-02-01 00:00:00" ]]; then
    echo "Employment-history query did not reconstruct the pre-correction system-time version: ${history_before}" >&2
    exit 1
fi

history_after="$(run_employment_history_query \
    '10000000-0000-7000-8000-000000000001' \
    '00000000-0000-7000-8000-000000000001' \
    '2026-02-15 00:00:00+00' \
    'Pacific/Honolulu')"
IFS='|' read -r history_tenant history_person history_employment history_version history_status \
    history_concurrency history_effective_from history_effective_to history_recorded_from history_recorded_to \
    <<<"${history_after}"
if [[ "${history_employment}" != "00000000-0000-7000-8000-000000000024" \
   || "${history_version}" != "00000000-0000-7000-8000-000000000026" \
   || "${history_status}" != "leave" \
   || "${history_concurrency}" != "concurrent" \
   || "${history_recorded_from}" != "2026-02-01 00:00:00" \
   || -n "${history_recorded_to}" ]]; then
    echo "Employment-history query did not reconstruct the post-correction system-time version: ${history_after}" >&2
    exit 1
fi

history_at_boundary="$(run_employment_history_query \
    '10000000-0000-7000-8000-000000000001' \
    '00000000-0000-7000-8000-000000000001' \
    '2026-02-01 00:00:00+00' \
    'UTC')"
if [[ "${history_at_boundary}" != *"|00000000-0000-7000-8000-000000000026|leave|concurrent|"* \
   || "${history_at_boundary}" == *"00000000-0000-7000-8000-000000000025"* ]]; then
    echo "Employment-history query violated the half-open recorded-time boundary: ${history_at_boundary}" >&2
    exit 1
fi

foreign_history="$(run_employment_history_query \
    '10000000-0000-7000-8000-000000000001' \
    '00000000-0000-7000-8000-000000000101' \
    '2026-02-15 00:00:00+00' \
    'UTC')"
if [[ -n "${foreign_history}" ]]; then
    echo "Employment-history query exposed a foreign-tenant Person row: ${foreign_history}" >&2
    exit 1
fi

set +e
read_only_output="$({ psql "${DATABASE_URL}" -X -q -v ON_ERROR_STOP=1 <<SQL
BEGIN;
\i ${history_contract_tmp}/transaction.sql
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('30000000-0000-7000-8000-000000000001', 'must_not_write');
ROLLBACK;
SQL
} 2>&1)"
read_only_status=$?
set -e
if [[ ${read_only_status} -eq 0 ]]; then
    echo "Employment-history read-only transaction unexpectedly accepted a write" >&2
    exit 1
fi
if [[ "${read_only_output}" != *"read-only transaction"* ]]; then
    echo "Employment-history write rejection failed for an unexpected reason: ${read_only_output}" >&2
    exit 1
fi

trap - EXIT
rm -rf "${history_contract_tmp}"
echo "PostgreSQL bitemporal and Employment-history read contract passed"
