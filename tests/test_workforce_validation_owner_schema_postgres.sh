#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

migration="services/workforce-validation-api/database/migrations/0001_owner_schema.sql"
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"

role_flags="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolinherit, rolreplication, rolbypassrls
FROM pg_roles
WHERE rolname = 'workforce_validation_role';
")"
if [[ "${role_flags}" != "f|f|f|f|f|f|f" ]]; then
    echo "workforce_validation_role flags are not deny-default: ${role_flags}" >&2
    exit 1
fi

schema_owner="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT pg_get_userbyid(nspowner)
FROM pg_namespace
WHERE nspname = 'workforce_validation';
")"
if [[ "${schema_owner}" != "workforce_validation_role" ]]; then
    echo "workforce_validation schema has unexpected owner: ${schema_owner}" >&2
    exit 1
fi

role_config="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT COALESCE(array_to_string(rolconfig, ','), '')
FROM pg_roles
WHERE rolname = 'workforce_validation_role';
")"
if [[ -n "${role_config}" ]]; then
    echo "NOLOGIN schema owner must not carry ineffective login-only runtime defaults: ${role_config}" >&2
    exit 1
fi

set_role_probe="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SET search_path = public;
SET ROLE workforce_validation_role;
SELECT current_user || '|' || current_setting('search_path');
RESET ROLE;
")"
if [[ "${set_role_probe}" != "workforce_validation_role|public" ]]; then
    echo "unexpected SET ROLE search_path behavior: ${set_role_probe}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -qc "CREATE ROLE workforce_validation_public_probe NOLOGIN;"
trap 'psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -qc "DROP ROLE IF EXISTS workforce_validation_public_probe;" >/dev/null 2>&1 || true' EXIT

public_usage="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT has_schema_privilege('workforce_validation_public_probe', 'workforce_validation', 'USAGE');
")"
public_create="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT has_schema_privilege('workforce_validation_public_probe', 'workforce_validation', 'CREATE');
")"
if [[ "${public_usage}" != "f" || "${public_create}" != "f" ]]; then
    echo "PUBLIC retains workforce_validation schema privileges: usage=${public_usage} create=${public_create}" >&2
    exit 1
fi

relation_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_class AS relation
JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
WHERE namespace.nspname = 'workforce_validation';
")"
if [[ "${relation_count}" != "0" ]]; then
    echo "owner-schema bootstrap created application relations prematurely: ${relation_count}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -qc "DROP ROLE workforce_validation_public_probe;"
trap - EXIT
