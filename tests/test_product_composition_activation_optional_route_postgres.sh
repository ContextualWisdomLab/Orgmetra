#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
for migration in \
    database/migrations/0018_product_composition_generation_registry.sql \
    database/migrations/0019_product_composition_activation_registry.sql \
    database/migrations/0020_product_composition_activation_authority_enforcement.sql \
    database/migrations/0021_product_composition_activation_observation_wall_clock.sql \
    database/migrations/0022_product_composition_recovery_attestation.sql \
    database/migrations/0023_product_composition_deployment_write_serialization.sql \
    database/migrations/0024_product_composition_activation_trigger_function_provenance.sql \
    database/migrations/0025_product_composition_activation_relation_owner_provenance.sql
do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO product_composition_generation (
    generation_id, schema_version, config_sha256
) VALUES (
    'generation_optional',
    'orgmetra_gateway_composition.v1',
    repeat('a', 64)
);

INSERT INTO product_composition_owner_release (
    generation_id, service_id, release_version, openapi_sha256,
    artifact_sha256, release_locator
) VALUES
(
    'generation_optional', 'people_api', 'v1.2.3', repeat('1', 64), repeat('2', 64),
    'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3'
),
(
    'generation_optional', 'workforce_validation_api', 'v2.0.0', repeat('3', 64), repeat('4', 64),
    'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v2.0.0'
);

INSERT INTO product_composition_route (
    generation_id, route_id, path_template, owner_service_id, logical_upstream, required
) VALUES
(
    'generation_optional', 'people_get', '/v1/people/{person_record_id}',
    'people_api', 'service://people-api', TRUE
),
(
    'generation_optional', 'workforce_validation', '/v1/workforce/validation/{validation_id}',
    'workforce_validation_api', 'service://workforce-validation-api', FALSE
);

INSERT INTO product_composition_route_method (generation_id, route_id, method) VALUES
('generation_optional', 'people_get', 'GET'),
('generation_optional', 'workforce_validation', 'GET'),
('generation_optional', 'workforce_validation', 'POST');

INSERT INTO product_composition_deployment (deployment_id, environment_id) VALUES
('required_only_deployment', 'production'),
('partial_optional_deployment', 'production');
SQL

insert_evidence() {
    local bundle_digit="$1"
    local deployment_id="$2"
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO product_composition_activation_evidence (
    evidence_bundle_sha256, deployment_id, environment_id, generation_id, config_sha256,
    authorization_action, authorized_state_sequence,
    keyverse_release_version, keyverse_artifact_sha256, keyverse_release_locator,
    orgmetra_release_version, orgmetra_artifact_sha256, orgmetra_release_locator,
    orgmetra_policy_version_code, authorization_decision_sha256, valid_until_unix_ms
) VALUES (
    repeat('${bundle_digit}', 64), '${deployment_id}', 'production', 'generation_optional', repeat('a', 64),
    'activate', 0,
    'v1.0.0', repeat('5', 64),
    'https://github.com/ContextualWisdomLab/keyverse/releases/tag/v1.0.0',
    'v1.0.0', repeat('6', 64),
    'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.0.0',
    'composition_activation_v1', repeat('7', 64),
    floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint + 600000
);
SQL
}

insert_observation() {
    local bundle_digit="$1"
    local route_id="$2"
    local method="$3"
    local observation_digit="$4"
    local path_template service_id release_version openapi_digit artifact_digit
    if [[ "${route_id}" == "people_get" ]]; then
        path_template='/v1/people/{person_record_id}'
        service_id='people_api'
        release_version='v1.2.3'
        openapi_digit='1'
        artifact_digit='2'
    else
        path_template='/v1/workforce/validation/{validation_id}'
        service_id='workforce_validation_api'
        release_version='v2.0.0'
        openapi_digit='3'
        artifact_digit='4'
    fi

    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO product_composition_activation_owner_observation (
    evidence_bundle_sha256, generation_id, route_id, method, path_template,
    service_id, release_version, openapi_sha256, artifact_sha256,
    observation_sha256, observed_at_unix_ms, valid_until_unix_ms
)
SELECT
    repeat('${bundle_digit}', 64), 'generation_optional', '${route_id}', '${method}', '${path_template}',
    '${service_id}', '${release_version}', repeat('${openapi_digit}', 64), repeat('${artifact_digit}', 64),
    repeat('${observation_digit}', 64),
    floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint - 1000,
    valid_until_unix_ms
FROM product_composition_activation_evidence
WHERE evidence_bundle_sha256 = repeat('${bundle_digit}', 64);
SQL
}

insert_evidence 8 required_only_deployment
insert_observation 8 people_get GET 8

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO product_composition_activation_event (
    deployment_id, environment_id, activation_sequence, generation_id,
    previous_generation_id, event_kind, evidence_bundle_sha256
) VALUES (
    'required_only_deployment', 'production', 1, 'generation_optional',
    NULL, 'activate', repeat('8', 64)
);

INSERT INTO product_composition_activation_evidence (
    evidence_bundle_sha256, deployment_id, environment_id, generation_id, config_sha256,
    authorization_action, authorized_state_sequence,
    keyverse_release_version, keyverse_artifact_sha256, keyverse_release_locator,
    orgmetra_release_version, orgmetra_artifact_sha256, orgmetra_release_locator,
    orgmetra_policy_version_code, authorization_decision_sha256, valid_until_unix_ms
) VALUES (
    repeat('c', 64), 'required_only_deployment', 'production', 'generation_optional', repeat('a', 64),
    'recover', 1,
    'v1.0.0', repeat('5', 64),
    'https://github.com/ContextualWisdomLab/keyverse/releases/tag/v1.0.0',
    'v1.0.0', repeat('6', 64),
    'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.0.0',
    'composition_activation_v1', repeat('7', 64),
    floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint + 600000
);
SQL

insert_observation c people_get GET d

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO product_composition_recovery_attestation (
    deployment_id, environment_id, recovery_sequence, activation_sequence,
    generation_id, evidence_bundle_sha256
) VALUES (
    'required_only_deployment', 'production', 1, 1,
    'generation_optional', repeat('c', 64)
);
SQL

insert_evidence 9 partial_optional_deployment
insert_observation 9 people_get GET 8
insert_observation 9 workforce_validation GET 9

set +e
partial_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO product_composition_activation_event (
    deployment_id, environment_id, activation_sequence, generation_id,
    previous_generation_id, event_kind, evidence_bundle_sha256
) VALUES (
    'partial_optional_deployment', 'production', 1, 'generation_optional',
    NULL, 'activate', repeat('9', 64)
);
"; } 2>&1)"
partial_status=$?
set -e

if [[ ${partial_status} -eq 0 || "${partial_output}" != *"lacks fresh exact owner operation coverage"* ]]; then
    echo "partially observed optional route was not rejected: ${partial_output}" >&2
    exit 1
fi
