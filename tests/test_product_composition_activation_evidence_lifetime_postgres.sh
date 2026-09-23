#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0018_product_composition_generation_registry.sql \
    database/migrations/0019_product_composition_activation_registry.sql \
    database/migrations/0020_product_composition_activation_authority_enforcement.sql \
    database/migrations/0021_product_composition_activation_observation_wall_clock.sql \
    database/migrations/0022_product_composition_recovery_attestation.sql \
    database/migrations/0023_product_composition_deployment_write_serialization.sql \
    database/migrations/0024_product_composition_activation_trigger_function_provenance.sql \
    database/migrations/0025_product_composition_activation_relation_owner_provenance.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
INSERT INTO product_composition_generation (
    generation_id, schema_version, config_sha256
) VALUES (
    'generation_lifetime',
    'orgmetra_gateway_composition.v1',
    repeat('1', 64)
);
INSERT INTO product_composition_owner_release (
    generation_id, service_id, release_version, openapi_sha256,
    artifact_sha256, release_locator
) VALUES (
    'generation_lifetime', 'people_api', 'v1.2.1',
    repeat('2', 64), repeat('3', 64),
    'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.1'
);
INSERT INTO product_composition_route (
    generation_id, route_id, path_template, owner_service_id,
    logical_upstream, required
) VALUES (
    'generation_lifetime', 'people_get', '/v1/people/{person_record_id}',
    'people_api', 'service://people-api', TRUE
);
INSERT INTO product_composition_route_method (generation_id, route_id, method)
VALUES ('generation_lifetime', 'people_get', 'GET');
INSERT INTO product_composition_deployment (deployment_id, environment_id) VALUES
('activation_lifetime', 'production'),
('recovery_lifetime', 'production');
COMMIT;
SQL

insert_evidence() {
    local bundle_char="$1"
    local deployment_id="$2"
    local action="$3"
    local state_sequence="$4"
    local observation_char="$5"
    local observation_ttl_ms="$6"

    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
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
    repeat('${bundle_char}', 64),
    '${deployment_id}',
    'production',
    'generation_lifetime',
    repeat('1', 64),
    '${action}',
    ${state_sequence},
    'v1.0.0',
    repeat('4', 64),
    'https://github.com/ContextualWisdomLab/keyverse/releases/tag/v1.0.0',
    'v1.0.0',
    repeat('5', 64),
    'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.0.0',
    'composition_activation_v1',
    repeat('6', 64),
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
) VALUES (
    repeat('${bundle_char}', 64),
    'generation_lifetime',
    'people_get',
    'GET',
    '/v1/people/{person_record_id}',
    'people_api',
    'v1.2.1',
    repeat('2', 64),
    repeat('3', 64),
    repeat('${observation_char}', 64),
    floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint - 1000,
    floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint + ${observation_ttl_ms}
);
SQL
}

# Database authority must reject an activation bundle whose claimed validity exceeds
# the owner-operation observation supporting the required route.
insert_evidence a activation_lifetime activate 0 d 60000

set +e
activation_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO product_composition_activation_event (
    deployment_id,
    environment_id,
    activation_sequence,
    generation_id,
    previous_generation_id,
    event_kind,
    evidence_bundle_sha256
) VALUES (
    'activation_lifetime',
    'production',
    1,
    'generation_lifetime',
    NULL,
    'activate',
    repeat('a', 64)
);
"; } 2>&1)"
activation_status=$?
set -e
if [[ ${activation_status} -eq 0 || "${activation_output}" != *"lacks fresh exact owner operation coverage"* ]]; then
    echo "activation evidence outlived its owner observation: ${activation_output}" >&2
    exit 1
fi

# Seed a valid active state for the recovery case; here the observation lifetime is
# at least the evidence lifetime.
insert_evidence b recovery_lifetime activate 0 e 600000
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO product_composition_activation_event (
    deployment_id,
    environment_id,
    activation_sequence,
    generation_id,
    previous_generation_id,
    event_kind,
    evidence_bundle_sha256
) VALUES (
    'recovery_lifetime',
    'production',
    1,
    'generation_lifetime',
    NULL,
    'activate',
    repeat('b', 64)
);
SQL

# A recovery bundle can otherwise pass while its shorter owner observation expires
# first, letting a serving snapshot outlive the evidence that justified its route.
insert_evidence c recovery_lifetime recover 1 f 60000

set +e
recovery_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO product_composition_recovery_attestation (
    deployment_id,
    environment_id,
    recovery_sequence,
    activation_sequence,
    generation_id,
    evidence_bundle_sha256
) VALUES (
    'recovery_lifetime',
    'production',
    1,
    1,
    'generation_lifetime',
    repeat('c', 64)
);
"; } 2>&1)"
recovery_status=$?
set -e
if [[ ${recovery_status} -eq 0 || "${recovery_output}" != *"lacks fresh exact owner operation coverage"* ]]; then
    echo "recovery evidence outlived its owner observation: ${recovery_output}" >&2
    exit 1
fi
