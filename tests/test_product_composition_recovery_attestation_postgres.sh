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
    database/migrations/0024_product_composition_activation_trigger_function_provenance.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

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
    local bundle_char="$1"
    local action="$2"
    local state_sequence="$3"
    local observation_char="$4"
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
    'orgmetra_gateway',
    'production',
    'generation_one',
    repeat('a', 64),
    '${action}',
    ${state_sequence},
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
    repeat('${bundle_char}', 64),
    'generation_one',
    'people_get',
    'GET',
    '/v1/people/{person_record_id}',
    'people_api',
    'v1.2.1',
    repeat('1', 64),
    repeat('2', 64),
    repeat('${observation_char}', 64),
    floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint - 1000,
    valid_until_unix_ms
FROM product_composition_activation_evidence
WHERE evidence_bundle_sha256 = repeat('${bundle_char}', 64);
SQL
}

insert_evidence 7 activate 0 6

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
    'orgmetra_gateway',
    'production',
    1,
    'generation_one',
    NULL,
    'activate',
    repeat('7', 64)
);
SQL

insert_evidence 8 recover 1 9

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO product_composition_recovery_attestation (
    deployment_id,
    environment_id,
    recovery_sequence,
    activation_sequence,
    generation_id,
    evidence_bundle_sha256
) VALUES (
    'orgmetra_gateway',
    'production',
    1,
    1,
    'generation_one',
    repeat('8', 64)
);
SQL

positive_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM product_composition_recovery_attestation
WHERE deployment_id = 'orgmetra_gateway'
  AND environment_id = 'production'
  AND recovery_sequence = 1
  AND activation_sequence = 1
  AND generation_id = 'generation_one'
  AND evidence_bundle_sha256 = repeat('8', 64);
")"
if [[ "${positive_count}" != "1" ]]; then
    echo "fresh recovery evidence was not durably attested" >&2
    exit 1
fi

set +e
wrong_action_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO product_composition_recovery_attestation (
    deployment_id,
    environment_id,
    recovery_sequence,
    activation_sequence,
    generation_id,
    evidence_bundle_sha256
) VALUES (
    'orgmetra_gateway',
    'production',
    2,
    1,
    'generation_one',
    repeat('7', 64)
);
" ; } 2>&1)"
wrong_action_status=$?
set -e
if [[ ${wrong_action_status} -eq 0 || "${wrong_action_output}" != *"does not authorize exact active state"* ]]; then
    echo "non-recovery evidence was accepted as recovery authority: ${wrong_action_output}" >&2
    exit 1
fi

set +e
sequence_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO product_composition_recovery_attestation (
    deployment_id,
    environment_id,
    recovery_sequence,
    activation_sequence,
    generation_id,
    evidence_bundle_sha256
) VALUES (
    'orgmetra_gateway',
    'production',
    3,
    1,
    'generation_one',
    repeat('8', 64)
);
" ; } 2>&1)"
sequence_status=$?
set -e
if [[ ${sequence_status} -eq 0 || "${sequence_output}" != *"sequence must advance exactly by one"* ]]; then
    echo "recovery attestation sequence gap was not rejected: ${sequence_output}" >&2
    exit 1
fi

set +e
truncate_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "TRUNCATE product_composition_recovery_attestation CASCADE;" ; } 2>&1)"
truncate_status=$?
set -e
if [[ ${truncate_status} -eq 0 || "${truncate_output}" != *"append-only"* ]]; then
    echo "recovery attestation history allowed TRUNCATE: ${truncate_output}" >&2
    exit 1
fi
