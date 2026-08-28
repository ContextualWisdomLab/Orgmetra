#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0040_employment_employing_organization.sql

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference) VALUES
  ('10000000-0000-7000-8000-000000000001', 'tenant_alpha'),
  ('20000000-0000-7000-8000-000000000001', 'tenant_beta');

INSERT INTO person_record (tenant_record_id, person_record_id) VALUES
  ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000010'),
  ('20000000-0000-7000-8000-000000000001', '20000000-0000-7000-8000-000000000010');

INSERT INTO employment_record (tenant_record_id, employment_record_id, person_record_id) VALUES
  ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000020', '10000000-0000-7000-8000-000000000010'),
  ('20000000-0000-7000-8000-000000000001', '20000000-0000-7000-8000-000000000020', '20000000-0000-7000-8000-000000000010');

INSERT INTO employment_record_version (
  tenant_record_id, employment_record_version_id, employment_record_id,
  employment_status_code, effective_from, effective_to, recorded_from
) VALUES
  ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000021', '10000000-0000-7000-8000-000000000020', 'active', DATE '2026-01-01', NULL, TIMESTAMPTZ '2026-01-02 00:00:00+00'),
  ('20000000-0000-7000-8000-000000000001', '20000000-0000-7000-8000-000000000021', '20000000-0000-7000-8000-000000000020', 'active', DATE '2026-01-01', NULL, TIMESTAMPTZ '2026-01-02 00:00:00+00');

INSERT INTO organization_unit (tenant_record_id, organization_unit_id) VALUES
  ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000030'),
  ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000031'),
  ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000032'),
  ('20000000-0000-7000-8000-000000000001', '20000000-0000-7000-8000-000000000030');

INSERT INTO organization_unit_version (
  tenant_record_id, organization_unit_version_id, organization_unit_id,
  unit_name, organization_type_code, effective_from, effective_to, recorded_from
) VALUES
  ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000040', '10000000-0000-7000-8000-000000000030', 'Alpha Legal Employer', 'legal_entity', DATE '2026-01-01', NULL, TIMESTAMPTZ '2026-01-02 00:00:00+00'),
  ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000041', '10000000-0000-7000-8000-000000000031', 'Alpha Second Employer', 'legal_entity', DATE '2026-01-01', NULL, TIMESTAMPTZ '2026-01-02 00:00:00+00'),
  ('10000000-0000-7000-8000-000000000001', '10000000-0000-7000-8000-000000000042', '10000000-0000-7000-8000-000000000032', 'People Department', 'department', DATE '2026-01-01', NULL, TIMESTAMPTZ '2026-01-02 00:00:00+00'),
  ('20000000-0000-7000-8000-000000000001', '20000000-0000-7000-8000-000000000040', '20000000-0000-7000-8000-000000000030', 'Beta Legal Employer', 'legal_entity', DATE '2026-01-01', NULL, TIMESTAMPTZ '2026-01-02 00:00:00+00');

INSERT INTO employment_employing_organization_record (
  tenant_record_id, employment_employing_organization_record_id,
  employment_record_id, employing_organization_unit_id,
  effective_from, effective_to, recorded_from
) VALUES (
  '10000000-0000-7000-8000-000000000001',
  '10000000-0000-7000-8000-000000000050',
  '10000000-0000-7000-8000-000000000020',
  '10000000-0000-7000-8000-000000000030',
  DATE '2026-01-01', NULL, TIMESTAMPTZ '2026-01-03 00:00:00+00'
);
SQL

current_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM employment_employing_organization_record
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'::uuid
  AND employment_record_id = '10000000-0000-7000-8000-000000000020'::uuid
  AND daterange(effective_from, effective_to, '[)') @> DATE '2026-08-28'
  AND tstzrange(recorded_from, recorded_to, '[)') @> TIMESTAMPTZ '2026-08-28 00:00:00+00';
")"
[[ "${current_count}" == "1" ]] || { echo "expected exactly one employer at one business/system coordinate, got ${current_count}" >&2; exit 1; }

set +e
overlap_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO employment_employing_organization_record (
  tenant_record_id, employment_employing_organization_record_id,
  employment_record_id, employing_organization_unit_id,
  effective_from, recorded_from
) VALUES (
  '10000000-0000-7000-8000-000000000001',
  '10000000-0000-7000-8000-000000000051',
  '10000000-0000-7000-8000-000000000020',
  '10000000-0000-7000-8000-000000000031',
  DATE '2026-06-01', TIMESTAMPTZ '2026-01-04 00:00:00+00'
);
SQL
} 2>&1)"
overlap_status=$?
set -e
[[ ${overlap_status} -ne 0 && "${overlap_output}" == *"employment_employing_organization_bitemporal_exclusion"* ]] || {
  echo "overlapping employing organization did not fail at the bitemporal exclusion: ${overlap_output}" >&2; exit 1;
}

set +e
non_legal_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO employment_employing_organization_record (
  tenant_record_id, employment_employing_organization_record_id,
  employment_record_id, employing_organization_unit_id,
  effective_from, effective_to, recorded_from
) VALUES (
  '10000000-0000-7000-8000-000000000001',
  '10000000-0000-7000-8000-000000000052',
  '10000000-0000-7000-8000-000000000020',
  '10000000-0000-7000-8000-000000000032',
  DATE '2025-01-01', DATE '2025-06-01', TIMESTAMPTZ '2026-01-03 00:00:00+00'
);
SQL
} 2>&1)"
non_legal_status=$?
set -e
[[ ${non_legal_status} -ne 0 && "${non_legal_output}" == *"employing organization must be a legal_entity"* ]] || {
  echo "department was accepted as an employing legal entity: ${non_legal_output}" >&2; exit 1;
}

set +e
cross_tenant_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO employment_employing_organization_record (
  tenant_record_id, employment_employing_organization_record_id,
  employment_record_id, employing_organization_unit_id,
  effective_from, recorded_from
) VALUES (
  '10000000-0000-7000-8000-000000000001',
  '10000000-0000-7000-8000-000000000053',
  '10000000-0000-7000-8000-000000000020',
  '20000000-0000-7000-8000-000000000030',
  DATE '2025-01-01', TIMESTAMPTZ '2026-01-03 00:00:00+00'
);
SQL
} 2>&1)"
cross_tenant_status=$?
set -e
[[ ${cross_tenant_status} -ne 0 && "${cross_tenant_output}" == *"employment_employing_organization_unit_tenant_fk"* ]] || {
  echo "cross-tenant employer reference was not rejected by tenant-qualified integrity: ${cross_tenant_output}" >&2; exit 1;
}

set +e
rewrite_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
UPDATE employment_employing_organization_record
SET employing_organization_unit_id = '10000000-0000-7000-8000-000000000031'
WHERE employment_employing_organization_record_id = '10000000-0000-7000-8000-000000000050';
"; } 2>&1)"
rewrite_status=$?
set -e
[[ ${rewrite_status} -ne 0 && "${rewrite_output}" == *"bitemporal correction may only close an open recorded interval"* ]] || {
  echo "in-place employer rewrite was not rejected: ${rewrite_output}" >&2; exit 1;
}

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE employment_employing_organization_record
SET recorded_to = TIMESTAMPTZ '2026-09-01 00:00:00+00'
WHERE employment_employing_organization_record_id = '10000000-0000-7000-8000-000000000050';

INSERT INTO employment_employing_organization_record (
  tenant_record_id, employment_employing_organization_record_id,
  employment_record_id, employing_organization_unit_id,
  effective_from, effective_to, recorded_from
) VALUES (
  '10000000-0000-7000-8000-000000000001',
  '10000000-0000-7000-8000-000000000054',
  '10000000-0000-7000-8000-000000000020',
  '10000000-0000-7000-8000-000000000031',
  DATE '2026-01-01', NULL, TIMESTAMPTZ '2026-09-01 00:00:00+00'
);

CREATE ROLE orgmetra_employer_reader NOSUPERUSER NOBYPASSRLS;
GRANT SELECT ON employment_employing_organization_record TO orgmetra_employer_reader;
SET ROLE orgmetra_employer_reader;
SELECT set_config('orgmetra.tenant_record_id', '10000000-0000-7000-8000-000000000001', false);
DO $$
BEGIN
  IF (SELECT count(*) FROM employment_employing_organization_record) <> 1 THEN
    RAISE EXCEPTION 'tenant alpha should see exactly one current-system employer fact';
  END IF;
END
$$;
SELECT set_config('orgmetra.tenant_record_id', '20000000-0000-7000-8000-000000000001', false);
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM employment_employing_organization_record) THEN
    RAISE EXCEPTION 'tenant beta unexpectedly observed tenant alpha employer facts';
  END IF;
END
$$;
RESET ROLE;
SQL

echo "Employment employing-organization PostgreSQL contract passed"
