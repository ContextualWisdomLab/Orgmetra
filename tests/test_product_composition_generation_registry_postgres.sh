#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -f database/migrations/0018_product_composition_generation_registry.sql

GENERATION_ID="generation_postgres_contract"
CONFIG_SHA="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
OPENAPI_SHA="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
ARTIFACT_SHA="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
BEGIN;
INSERT INTO product_composition_generation (
    generation_id, schema_version, config_sha256
) VALUES (
    '${GENERATION_ID}',
    'orgmetra_gateway_composition.v1',
    '${CONFIG_SHA}'
);
INSERT INTO product_composition_owner_release (
    generation_id, service_id, release_version, openapi_sha256,
    artifact_sha256, release_locator
) VALUES (
    '${GENERATION_ID}', 'people_api', 'v1.2.3', '${OPENAPI_SHA}',
    '${ARTIFACT_SHA}',
    'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3'
);
INSERT INTO product_composition_route (
    generation_id, route_id, path_template, owner_service_id,
    logical_upstream, required
) VALUES (
    '${GENERATION_ID}', 'people_get', '/v1/people/{person_record_id}',
    'people_api', 'service://people-api', TRUE
);
INSERT INTO product_composition_route_method (generation_id, route_id, method)
VALUES
    ('${GENERATION_ID}', 'people_get', 'GET'),
    ('${GENERATION_ID}', 'people_get', 'HEAD');
COMMIT;
SQL

method_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM product_composition_route_method
WHERE generation_id = '${GENERATION_ID}';
")"
if [[ "${method_count}" != "2" ]]; then
    echo "normalized composition route methods did not persist atomically" >&2
    exit 1
fi

set +e
reassign_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO product_composition_generation (
    generation_id, schema_version, config_sha256
) VALUES (
    '${GENERATION_ID}',
    'orgmetra_gateway_composition.v1',
    'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd'
);
" ; } 2>&1)"
reassign_status=$?
set -e
if [[ ${reassign_status} -eq 0 ]]; then
    echo "generation_id was reassigned to different configuration material" >&2
    exit 1
fi

set +e
update_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
UPDATE product_composition_generation
SET config_sha256 = 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
WHERE generation_id = '${GENERATION_ID}';
" ; } 2>&1)"
update_status=$?
set -e
if [[ ${update_status} -eq 0 || "${update_output}" != *"append-only"* ]]; then
    echo "generation registry allowed destructive update: ${update_output}" >&2
    exit 1
fi

set +e
delete_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
DELETE FROM product_composition_route
WHERE generation_id = '${GENERATION_ID}' AND route_id = 'people_get';
" ; } 2>&1)"
delete_status=$?
set -e
if [[ ${delete_status} -eq 0 || "${delete_output}" != *"append-only"* ]]; then
    echo "generation registry allowed destructive delete: ${delete_output}" >&2
    exit 1
fi

set +e
partial_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
BEGIN;
INSERT INTO product_composition_generation (
    generation_id, schema_version, config_sha256
) VALUES (
    'generation_partial',
    'orgmetra_gateway_composition.v1',
    'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'
);
INSERT INTO product_composition_route (
    generation_id, route_id, path_template, owner_service_id,
    logical_upstream, required
) VALUES (
    'generation_partial', 'people_get', '/v1/people/{person_record_id}',
    'missing_owner', 'service://missing-owner', TRUE
);
COMMIT;
SQL
} 2>&1)"
partial_status=$?
set -e
if [[ ${partial_status} -eq 0 ]]; then
    echo "partial registry transaction unexpectedly committed" >&2
    exit 1
fi

partial_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM product_composition_generation
WHERE generation_id = 'generation_partial';
")"
if [[ "${partial_count}" != "0" ]]; then
    echo "failed registry transaction left partial generation state" >&2
    echo "${partial_output}" >&2
    exit 1
fi
