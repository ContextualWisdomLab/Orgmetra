#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0018_product_composition_generation_registry.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0019_product_composition_activation_registry.sql

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
INSERT INTO product_composition_generation (
    generation_id, schema_version, config_sha256
) VALUES (
    'generation_one',
    'orgmetra_gateway_composition.v1',
    repeat('a', 64)
);
INSERT INTO product_composition_deployment (deployment_id, environment_id)
VALUES ('orgmetra_gateway', 'production');
COMMIT;
SQL

# Hold a predecessor-schema structural activation open while 0020 starts. Readiness is
# observed through PostgreSQL state, not an assumed scheduling delay. The corrected migration
# must wait at its writer-conflicting fence, then see the committed NULL-evidence event during
# preflight and roll the authority upgrade back as one unit.
PGAPPNAME=orgmetra_activation_authority_upgrade_writer \
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL' &
BEGIN;
INSERT INTO product_composition_activation_event (
    deployment_id,
    environment_id,
    activation_sequence,
    generation_id,
    previous_generation_id,
    event_kind
) VALUES (
    'orgmetra_gateway',
    'production',
    1,
    'generation_one',
    NULL,
    'activate'
);
SELECT pg_sleep(5);
COMMIT;
SQL
writer_pid=$!

writer_ready=0
for _ in {1..50}; do
    writer_ready="$({ psql "${DATABASE_URL}" -Atqc \
        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND application_name = 'orgmetra_activation_authority_upgrade_writer' AND state = 'active' AND query LIKE 'SELECT pg_sleep(%'; } 2>/dev/null)"
    if [[ "${writer_ready}" == "1" ]]; then
        break
    fi
    sleep 0.1
done

if [[ "${writer_ready}" != "1" ]]; then
    wait "${writer_pid}" || true
    echo "writer was not observed inside the predecessor activation transaction" >&2
    exit 1
fi

set +e
upgrade_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -f database/migrations/0020_product_composition_activation_authority_enforcement.sql; } 2>&1)"
upgrade_status=$?
set -e
wait "${writer_pid}"

if [[ ${upgrade_status} -eq 0 || "${upgrade_output}" != *"cannot enforce authorized activation while structural events exist"* ]]; then
    echo "0020 did not fence predecessor activation history before authority preflight: ${upgrade_output}" >&2
    exit 1
fi

is_nullable="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'product_composition_activation_event'
  AND column_name = 'evidence_bundle_sha256';
")"
if [[ "${is_nullable}" != "YES" ]]; then
    echo "failed 0020 upgrade partially published NOT NULL authority" >&2
    exit 1
fi
