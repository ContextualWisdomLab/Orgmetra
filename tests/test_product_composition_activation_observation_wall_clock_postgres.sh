#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0018_product_composition_generation_registry.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0019_product_composition_activation_registry.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0020_product_composition_activation_authority_enforcement.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0021_product_composition_activation_observation_wall_clock.sql

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
INSERT INTO product_composition_generation (
    generation_id, schema_version, config_sha256
) VALUES (
    'generation_one',
    'orgmetra_gateway_composition.v1',
    repeat('a', 64)
);
INSERT INTO product_composition_owner_release (
    generation_id, service_id, release_version, openapi_sha256,
    artifact_sha256, release_locator
) VALUES (
    'generation_one', 'people_api', 'v1.2.1',
    repeat('1', 64), repeat('2', 64),
    'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.1'
);
INSERT INTO product_composition_route (
    generation_id, route_id, path_template, owner_service_id,
    logical_upstream, required
) VALUES (
    'generation_one', 'people_get', '/v1/people/{person_record_id}',
    'people_api', 'service://people-api', TRUE
);
INSERT INTO product_composition_route_method (generation_id, route_id, method)
VALUES ('generation_one', 'people_get', 'GET');
INSERT INTO product_composition_deployment (deployment_id, environment_id)
VALUES ('orgmetra_gateway', 'production');
COMMIT;
SQL

insert_evidence() {
    local bundle_digit="$1"
    local valid_offset_ms="$2"
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
        -v bundle_digit="${bundle_digit}" \
        -v valid_offset_ms="${valid_offset_ms}" <<'SQL'
INSERT INTO product_composition_activation_evidence (
    evidence_bundle_sha256,
    deployment_id,
    environment_id,
    generation_id,
    config_sha256,
    authorization_action,
    authorized_state_sequence,
    keyverse_release_version,
    keyverse_artifact_sha256,
    keyverse_release_locator,
    orgmetra_release_version,
    orgmetra_artifact_sha256,
    orgmetra_release_locator,
    orgmetra_policy_version_code,
    authorization_decision_sha256,
    valid_until_unix_ms
) VALUES (
    repeat(:'bundle_digit', 64),
    'orgmetra_gateway',
    'production',
    'generation_one',
    repeat('a', 64),
    'activate',
    0,
    'v1.0.0',
    repeat('3', 64),
    'https://github.com/ContextualWisdomLab/keyverse/releases/tag/v1.0.0',
    'v1.0.0',
    repeat('4', 64),
    'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.0.0',
    'composition_activation_v1',
    repeat('5', 64),
    floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint + :'valid_offset_ms'::bigint
);
SQL
}

insert_evidence 7 600000

set +e
future_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO product_composition_activation_owner_observation (
    evidence_bundle_sha256, generation_id, route_id, method, path_template,
    service_id, release_version, openapi_sha256, artifact_sha256,
    observation_sha256, observed_at_unix_ms, valid_until_unix_ms
)
SELECT
    repeat('7', 64), 'generation_one', 'people_get', 'GET',
    '/v1/people/{person_record_id}', 'people_api', 'v1.2.1',
    repeat('1', 64), repeat('2', 64), repeat('6', 64),
    floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint + 60000,
    valid_until_unix_ms
FROM product_composition_activation_evidence
WHERE evidence_bundle_sha256 = repeat('7', 64);
SQL
} 2>&1)"
future_status=$?
set -e
if [[ ${future_status} -eq 0 || "${future_output}" != *"cannot be dated after database wall clock"* ]]; then
    echo "future-dated owner observation was not rejected by PostgreSQL: ${future_output}" >&2
    exit 1
fi

insert_evidence 8 -1000

set +e
stale_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO product_composition_activation_owner_observation (
    evidence_bundle_sha256, generation_id, route_id, method, path_template,
    service_id, release_version, openapi_sha256, artifact_sha256,
    observation_sha256, observed_at_unix_ms, valid_until_unix_ms
)
SELECT
    repeat('8', 64), 'generation_one', 'people_get', 'GET',
    '/v1/people/{person_record_id}', 'people_api', 'v1.2.1',
    repeat('1', 64), repeat('2', 64), repeat('9', 64),
    valid_until_unix_ms - 1000,
    valid_until_unix_ms
FROM product_composition_activation_evidence
WHERE evidence_bundle_sha256 = repeat('8', 64);
SQL
} 2>&1)"
stale_status=$?
set -e
if [[ ${stale_status} -eq 0 || "${stale_output}" != *"must be fresh when persisted"* ]]; then
    echo "already-stale owner observation was not rejected by PostgreSQL: ${stale_output}" >&2
    exit 1
fi

insert_evidence 9 600000
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO product_composition_activation_owner_observation (
    evidence_bundle_sha256, generation_id, route_id, method, path_template,
    service_id, release_version, openapi_sha256, artifact_sha256,
    observation_sha256, observed_at_unix_ms, valid_until_unix_ms
)
SELECT
    repeat('9', 64), 'generation_one', 'people_get', 'GET',
    '/v1/people/{person_record_id}', 'people_api', 'v1.2.1',
    repeat('1', 64), repeat('2', 64), repeat('0', 64),
    floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint - 1000,
    valid_until_unix_ms
FROM product_composition_activation_evidence
WHERE evidence_bundle_sha256 = repeat('9', 64);
SQL

valid_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM product_composition_activation_owner_observation
WHERE evidence_bundle_sha256 = repeat('9', 64);
")"
if [[ "${valid_count}" != "1" ]]; then
    echo "fresh owner observation did not persist exactly once" >&2
    exit 1
fi
