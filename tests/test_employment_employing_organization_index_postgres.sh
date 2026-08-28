#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

index_definition="$(psql "${DATABASE_URL}" -Atqc "SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'employment_employing_organization_record' AND indexname = 'employment_employing_organization_unit_lookup_index';")"

[[ -n "${index_definition}" ]] || {
  echo "missing employment_employing_organization_unit_lookup_index" >&2
  exit 1
}

[[ "${index_definition}" == *"(tenant_record_id, employing_organization_unit_id)"* ]] || {
  echo "employment_employing_organization_unit_lookup_index does not cover tenant_record_id and employing_organization_unit_id: ${index_definition}" >&2
  exit 1
}
