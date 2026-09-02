#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0012_people_mutation_idempotency.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0017_assignment_category_code.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0018_assignment_category_supersession.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0019_assignment_correction_idempotency_route.sql

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO public.tenant_record (tenant_record_id, tenant_reference)
VALUES ('30000000-0000-7000-8000-000000000001', 'correction_idempotency_tenant');

INSERT INTO public.people_mutation_idempotency_record (
    tenant_record_id,
    people_mutation_idempotency_record_id,
    command_route,
    idempotency_key,
    command_digest,
    created_record_id
) VALUES (
    '30000000-0000-7000-8000-000000000001',
    '30000000-0000-7000-8000-000000000011',
    'assignment-category-corrections',
    'assignment-correction-17xx',
    repeat('a', 64),
    '30000000-0000-7000-8000-000000000012'
);
SQL

route_count="$(psql "${DATABASE_URL}" -Atqc "SELECT count(*) FROM public.people_mutation_idempotency_record WHERE tenant_record_id='30000000-0000-7000-8000-000000000001' AND command_route='assignment-category-corrections';")"
test "${route_count}" = "1"

set +e
unknown_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "INSERT INTO public.people_mutation_idempotency_record (tenant_record_id, people_mutation_idempotency_record_id, command_route, idempotency_key, command_digest, created_record_id) VALUES ('30000000-0000-7000-8000-000000000001','30000000-0000-7000-8000-000000000013','assignment-correction-unknown','assignment-correction-18xx',repeat('b',64),'30000000-0000-7000-8000-000000000014');" 2>&1)"
unknown_status=$?
set -e
if [[ ${unknown_status} -eq 0 || "${unknown_output}" != *"people_mutation_idempotency_route_check"* ]]; then
    echo "unknown People mutation route escaped the closed idempotency vocabulary: ${unknown_output}" >&2
    exit 1
fi
