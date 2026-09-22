#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0018_product_composition_generation_registry.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0019_product_composition_activation_registry.sql

seed_generation() {
    local generation_id="$1"
    local config_sha="$2"
    local patch="$3"
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
    '${generation_id}', 'people_api', 'v1.2.${patch}',
    '1111111111111111111111111111111111111111111111111111111111111111',
    '2222222222222222222222222222222222222222222222222222222222222222',
    'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.${patch}'
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

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO product_composition_deployment (deployment_id, environment_id)
VALUES ('orgmetra_gateway', 'production');

INSERT INTO product_composition_activation_evidence (
    evidence_bundle_sha256,
    deployment_id,
    environment_id,
    generation_id,
    config_sha256,
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
    repeat('7', 64),
    'orgmetra_gateway',
    'production',
    'generation_one',
    repeat('a', 64),
    'v1.0.0',
    repeat('3', 64),
    'https://github.com/ContextualWisdomLab/keyverse/releases/tag/v1.0.0',
    'v1.0.0',
    repeat('4', 64),
    'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.0.0',
    'composition_activation_v1',
    repeat('5', 64),
    floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint + 600000
);

INSERT INTO product_composition_activation_owner_observation (
    evidence_bundle_sha256,
    generation_id,
    route_id,
    method,
    path_template,
    service_id,
    release_version,
    openapi_sha256,
    artifact_sha256,
    observation_sha256,
    observed_at_unix_ms,
    valid_until_unix_ms
)
SELECT
    repeat('7', 64),
    'generation_one',
    'people_get',
    'GET',
    '/v1/people/{person_record_id}',
    'people_api',
    'v1.2.1',
    repeat('1', 64),
    repeat('2', 64),
    repeat('6', 64),
    floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint - 1000,
    valid_until_unix_ms
FROM product_composition_activation_evidence
WHERE evidence_bundle_sha256 = repeat('7', 64);

INSERT INTO product_composition_activation_event (
    deployment_id,
    environment_id,
    activation_sequence,
    generation_id,
    previous_generation_id,
    event_kind,
    evidence_bundle_sha256
) VALUES (
    'orgmetra_gateway',
    'production',
    1,
    'generation_one',
    NULL,
    'activate',
    repeat('7', 64)
);
SQL

positive_bundle="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT evidence_bundle_sha256
FROM product_composition_activation_event
WHERE deployment_id = 'orgmetra_gateway'
  AND environment_id = 'production'
  AND activation_sequence = 1;
")"
if [[ "${positive_bundle}" != "$(printf '7%.0s' {1..64})" ]]; then
    echo "activation did not retain exact evidence bundle attribution" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO product_composition_activation_evidence (
    evidence_bundle_sha256,
    deployment_id,
    environment_id,
    generation_id,
    config_sha256,
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
    repeat('8', 64),
    'orgmetra_gateway',
    'production',
    'generation_two',
    repeat('b', 64),
    'v1.0.0',
    repeat('3', 64),
    'https://github.com/ContextualWisdomLab/keyverse/releases/tag/v1.0.0',
    'v1.0.0',
    repeat('4', 64),
    'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.0.0',
    'composition_activation_v1',
    repeat('5', 64),
    floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint - 1
);

INSERT INTO product_composition_activation_owner_observation (
    evidence_bundle_sha256,
    generation_id,
    route_id,
    method,
    path_template,
    service_id,
    release_version,
    openapi_sha256,
    artifact_sha256,
    observation_sha256,
    observed_at_unix_ms,
    valid_until_unix_ms
)
SELECT
    repeat('8', 64),
    'generation_two',
    'people_get',
    'GET',
    '/v1/people/{person_record_id}',
    'people_api',
    'v1.2.2',
    repeat('1', 64),
    repeat('2', 64),
    repeat('6', 64),
    valid_until_unix_ms - 10000,
    valid_until_unix_ms
FROM product_composition_activation_evidence
WHERE evidence_bundle_sha256 = repeat('8', 64);
SQL

set +e
expired_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO product_composition_activation_event (
    deployment_id,
    environment_id,
    activation_sequence,
    generation_id,
    previous_generation_id,
    event_kind,
    evidence_bundle_sha256
) VALUES (
    'orgmetra_gateway',
    'production',
    2,
    'generation_two',
    'generation_one',
    'activate',
    repeat('8', 64)
);
" ; } 2>&1)"
expired_status=$?
set -e
if [[ ${expired_status} -eq 0 || "${expired_output}" != *"activation authorization evidence is expired"* ]]; then
    echo "expired evidence was not rejected inside activation transaction: ${expired_output}" >&2
    exit 1
fi
