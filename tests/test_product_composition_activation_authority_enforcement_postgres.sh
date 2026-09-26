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

set +e
unauthorized_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO product_composition_activation_event (
    deployment_id, environment_id, activation_sequence,
    generation_id, previous_generation_id, event_kind
) VALUES (
    'orgmetra_gateway', 'production', 1,
    'generation_one', NULL, 'activate'
);
" ; } 2>&1)"
unauthorized_status=$?
set -e
if [[ ${unauthorized_status} -eq 0 || "${unauthorized_output}" != *"evidence_bundle_sha256"* ]]; then
    echo "current activation schema admitted an event without durable evidence: ${unauthorized_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
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
    repeat('7', 64),
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

persisted_bundle="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT evidence_bundle_sha256
FROM product_composition_activation_event
WHERE deployment_id = 'orgmetra_gateway'
  AND environment_id = 'production'
  AND activation_sequence = 1;
")"
if [[ "${persisted_bundle}" != "$(printf '7%.0s' {1..64})" ]]; then
    echo "authorized activation did not retain durable evidence attribution" >&2
    exit 1
fi
