#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -f database/migrations/0018_product_composition_generation_registry.sql

for table in \
    product_composition_generation \
    product_composition_owner_release \
    product_composition_route \
    product_composition_route_method
do
    set +e
    truncate_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "TRUNCATE TABLE ${table} CASCADE;"; } 2>&1)"
    truncate_status=$?
    set -e
    if [[ ${truncate_status} -eq 0 || "${truncate_output}" != *"append-only"* ]]; then
        echo "${table} allowed destructive TRUNCATE: ${truncate_output}" >&2
        exit 1
    fi
done
