#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0018_product_composition_generation_registry.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0019_product_composition_activation_registry.sql

seed_generation() {
    local generation_id="$1"
    local config_sha="$2"
    local suffix="$3"
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
BEGIN;
INSERT INTO product_composition_generation (
    generation_id, schema_version, config_sha256
) VALUES (
    '${generation_id}',
    'orgmetra_gateway_composition.v1',
    '${config_sha}'
);
INSERT INTO product_composition_owner_release (
    generation_id, service_id, release_version, openapi_sha256,
    artifact_sha256, release_locator
) VALUES (
    '${generation_id}', 'people_api', 'v1.2.${suffix}',
    '1111111111111111111111111111111111111111111111111111111111111111',
    '2222222222222222222222222222222222222222222222222222222222222222',
    'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.${suffix}'
);
INSERT INTO product_composition_route (
    generation_id, route_id, path_template, owner_service_id,
    logical_upstream, required
) VALUES (
    '${generation_id}', 'people_get', '/v1/people/{person_record_id}',
    'people_api', 'service://people-api', TRUE
);
INSERT INTO product_composition_route_method (generation_id, route_id, method)
VALUES ('${generation_id}', 'people_get', 'GET');
COMMIT;
SQL
}

seed_generation generation_one aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 1
seed_generation generation_two bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb 2
seed_generation generation_three cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc 3

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO product_composition_deployment (deployment_id, environment_id)
VALUES ('orgmetra_gateway', 'production');

INSERT INTO product_composition_activation_event (
    deployment_id, environment_id, activation_sequence,
    generation_id, previous_generation_id, event_kind
) VALUES (
    'orgmetra_gateway', 'production', 1,
    'generation_one', NULL, 'activate'
);

INSERT INTO product_composition_activation_event (
    deployment_id, environment_id, activation_sequence,
    generation_id, previous_generation_id, event_kind
) VALUES (
    'orgmetra_gateway', 'production', 2,
    'generation_two', 'generation_one', 'activate'
);

INSERT INTO product_composition_activation_event (
    deployment_id, environment_id, activation_sequence,
    generation_id, previous_generation_id, event_kind
) VALUES (
    'orgmetra_gateway', 'production', 3,
    'generation_one', 'generation_two', 'rollback'
);
SQL

active_generation="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT generation_id
FROM product_composition_activation_event
WHERE deployment_id = 'orgmetra_gateway' AND environment_id = 'production'
ORDER BY activation_sequence DESC
LIMIT 1;
")"
if [[ "${active_generation}" != "generation_one" ]]; then
    echo "rollback did not append the expected active generation" >&2
    exit 1
fi

set +e
stale_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO product_composition_activation_event (
    deployment_id, environment_id, activation_sequence,
    generation_id, previous_generation_id, event_kind
) VALUES (
    'orgmetra_gateway', 'production', 3,
    'generation_two', 'generation_one', 'activate'
);
" ; } 2>&1)"
stale_status=$?
set -e
if [[ ${stale_status} -eq 0 || "${stale_output}" != *"advance exactly by one"* ]]; then
    echo "stale activation sequence was not rejected: ${stale_output}" >&2
    exit 1
fi

set +e
unknown_rollback_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO product_composition_activation_event (
    deployment_id, environment_id, activation_sequence,
    generation_id, previous_generation_id, event_kind
) VALUES (
    'orgmetra_gateway', 'production', 4,
    'generation_three', 'generation_one', 'rollback'
);
" ; } 2>&1)"
unknown_rollback_status=$?
set -e
if [[ ${unknown_rollback_status} -eq 0 || "${unknown_rollback_output}" != *"previously active"* ]]; then
    echo "rollback to never-active generation was not rejected: ${unknown_rollback_output}" >&2
    exit 1
fi

set +e
update_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
UPDATE product_composition_activation_event
SET generation_id = 'generation_two'
WHERE deployment_id = 'orgmetra_gateway'
  AND environment_id = 'production'
  AND activation_sequence = 3;
" ; } 2>&1)"
update_status=$?
set -e
if [[ ${update_status} -eq 0 || "${update_output}" != *"append-only"* ]]; then
    echo "activation history allowed destructive update: ${update_output}" >&2
    exit 1
fi

set +e
delete_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
DELETE FROM product_composition_activation_event
WHERE deployment_id = 'orgmetra_gateway'
  AND environment_id = 'production'
  AND activation_sequence = 1;
" ; } 2>&1)"
delete_status=$?
set -e
if [[ ${delete_status} -eq 0 || "${delete_output}" != *"append-only"* ]]; then
    echo "activation history allowed destructive delete: ${delete_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO product_composition_deployment (deployment_id, environment_id)
VALUES ('orgmetra_gateway', 'staging');
INSERT INTO product_composition_activation_event (
    deployment_id, environment_id, activation_sequence,
    generation_id, previous_generation_id, event_kind
) VALUES (
    'orgmetra_gateway', 'staging', 1,
    'generation_two', NULL, 'activate'
);
SQL

staging_sequence="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT max(activation_sequence)
FROM product_composition_activation_event
WHERE deployment_id = 'orgmetra_gateway' AND environment_id = 'staging';
")"
if [[ "${staging_sequence}" != "1" ]]; then
    echo "activation sequence leaked across deployment/environment coordinates" >&2
    exit 1
fi
