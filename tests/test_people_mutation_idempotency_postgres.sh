#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0003_audit_outbox_persistence.sql \
    database/migrations/0004_outbox_delivery_claim.sql \
    database/migrations/0005_outbox_delivery_finalization.sql \
    database/migrations/0006_outbox_delivery_dead_letter.sql \
    database/migrations/0007_outbox_retry_exhaustion.sql \
    database/migrations/0008_audit_outbox_review_hardening.sql \
    database/migrations/0009_candidate_worker_conversion_governance.sql \
    database/migrations/0012_people_mutation_idempotency.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="10000000-0000-7000-8000-000000000001"
FOREIGN_TENANT_ID="20000000-0000-7000-8000-000000000001"
tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

digest_one="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
digest_two="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
digest_assignment="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"

assert_rejected() {
    local expected="$1"
    shift
    set +e
    local output
    output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "$*"; } 2>&1)"
    local status=$?
    set -e
    if [[ ${status} -eq 0 ]]; then
        echo "expected rejection but statement succeeded: $*" >&2
        exit 1
    fi
    if [[ "${output}" != *"${expected}"* ]]; then
        echo "statement failed for an unexpected reason: ${output}" >&2
        exit 1
    fi
}

employment_event='{"data":{"high_impact":true,"result_code":"employment_created"},"datacontenttype":"application/json","id":"00000000-0000-4000-8000-000000000141","orgmetraactor":"keyverse_subject:01JACTOROPAQUE","orgmetraconfirmation":"confirmation:01JCONFIRMOPAQUE","orgmetraevidence":"decision_evidence_set:v1","orgmetrapurpose":"workforce_admin","orgmetrareason":"employment_record_created","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:people_api","specversion":"1.0","subject":"employment_record:00000000-0000-7000-8000-000000000111","time":"2026-08-18T00:01:00Z","type":"orgmetra.people.employment_created"}'
assignment_event='{"data":{"high_impact":true,"result_code":"assignment_created"},"datacontenttype":"application/json","id":"00000000-0000-4000-8000-000000000143","orgmetraactor":"keyverse_subject:01JACTOROPAQUE","orgmetraconfirmation":"confirmation:01JCONFIRMOPAQUE","orgmetraevidence":"decision_evidence_set:v1","orgmetrapurpose":"workforce_admin","orgmetrareason":"assignment_record_created","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:people_api","specversion":"1.0","subject":"assignment_record:00000000-0000-7000-8000-000000000121","time":"2026-08-18T00:02:00Z","type":"orgmetra.people.assignment_created"}'
second_employment_event='{"data":{"high_impact":true,"result_code":"employment_created"},"datacontenttype":"application/json","id":"00000000-0000-4000-8000-000000000145","orgmetraactor":"keyverse_subject:01JACTOROPAQUE","orgmetraconfirmation":"confirmation:01JCONFIRMOPAQUE","orgmetraevidence":"decision_evidence_set:v1","orgmetrapurpose":"workforce_admin","orgmetrareason":"employment_record_created","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:people_api","specversion":"1.0","subject":"employment_record:00000000-0000-7000-8000-000000000112","time":"2026-08-18T00:03:00Z","type":"orgmetra.people.employment_created"}'

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES
    ('10000000-0000-7000-8000-000000000001', 'tenant_alpha'),
    ('20000000-0000-7000-8000-000000000001', 'tenant_beta');

INSERT INTO person_record (tenant_record_id, person_record_id, recorded_from)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000101',
    TIMESTAMPTZ '2026-08-18 00:00:00+00'
);

INSERT INTO organization_unit (tenant_record_id, organization_unit_id, recorded_from)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000104',
    TIMESTAMPTZ '2026-08-18 00:00:00+00'
);

INSERT INTO job_profile (tenant_record_id, job_profile_id, recorded_from)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000106',
    TIMESTAMPTZ '2026-08-18 00:00:00+00'
);

INSERT INTO position_record (
    tenant_record_id, position_record_id, organization_unit_id, job_profile_id, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000108',
    '00000000-0000-7000-8000-000000000104',
    '00000000-0000-7000-8000-000000000106',
    TIMESTAMPTZ '2026-08-18 00:00:00+00'
);
SQL

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v canonical_event="${employment_event}" <<SQL
BEGIN;
INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id, recorded_from
) VALUES (
    '${TENANT_ID}',
    '00000000-0000-7000-8000-000000000111',
    '00000000-0000-7000-8000-000000000101',
    TIMESTAMPTZ '2026-08-18 00:01:00+00'
);
SELECT record_audit_outbox_event(
    '${TENANT_ID}'::uuid,
    '00000000-0000-4000-8000-000000000141'::uuid,
    '00000000-0000-4000-8000-000000000151'::uuid,
    :'canonical_event',
    encode(digest(convert_to(:'canonical_event', 'UTF8'), 'sha256'), 'hex'),
    'orgmetra_domain_events'
);
INSERT INTO people_mutation_idempotency_record (
    tenant_record_id, people_mutation_idempotency_record_id, command_route,
    idempotency_key, command_digest, created_record_id
) VALUES (
    '${TENANT_ID}',
    '00000000-0000-7000-8000-000000000161',
    'employment-records',
    'idempotency-key-17xx',
    '${digest_one}',
    '00000000-0000-7000-8000-000000000111'
);
COMMIT;
SQL

set +e
duplicate_output="$({
    tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
        -v canonical_event="${second_employment_event}" <<SQL
BEGIN;
INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id, recorded_from
) VALUES (
    '${TENANT_ID}',
    '00000000-0000-7000-8000-000000000112',
    '00000000-0000-7000-8000-000000000101',
    TIMESTAMPTZ '2026-08-18 00:03:00+00'
);
SELECT record_audit_outbox_event(
    '${TENANT_ID}'::uuid,
    '00000000-0000-4000-8000-000000000145'::uuid,
    '00000000-0000-4000-8000-000000000155'::uuid,
    :'canonical_event',
    encode(digest(convert_to(:'canonical_event', 'UTF8'), 'sha256'), 'hex'),
    'orgmetra_domain_events'
);
INSERT INTO people_mutation_idempotency_record (
    tenant_record_id, people_mutation_idempotency_record_id, command_route,
    idempotency_key, command_digest, created_record_id
) VALUES (
    '${TENANT_ID}',
    '00000000-0000-7000-8000-000000000162',
    'employment-records',
    'idempotency-key-17xx',
    '${digest_two}',
    '00000000-0000-7000-8000-000000000112'
);
COMMIT;
SQL
} 2>&1)"
duplicate_status=$?
set -e
if [[ ${duplicate_status} -eq 0 ]]; then
    echo "same tenant+route+key accepted a second employment/audit/outbox write" >&2
    exit 1
fi
if [[ "${duplicate_output}" != *"people_mutation_idempotency_command_unique"* && "${duplicate_output}" != *"duplicate key"* ]]; then
    echo "same-key retry failed for an unexpected reason: ${duplicate_output}" >&2
    exit 1
fi

employment_count="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "SELECT count(*) FROM employment_record;")"
audit_count="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "SELECT count(*) FROM audit_event_record;")"
outbox_count="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "SELECT count(*) FROM outbox_delivery_record;")"
idempotency_count="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "SELECT count(*) FROM people_mutation_idempotency_record;")"
if [[ "${employment_count}" != "1" || "${audit_count}" != "1" || "${outbox_count}" != "1" || "${idempotency_count}" != "1" ]]; then
    echo "same-key retry left extra HRIS/audit/outbox/idempotency facts: employment=${employment_count} audit=${audit_count} outbox=${outbox_count} idempotency=${idempotency_count}" >&2
    exit 1
fi

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v canonical_event="${second_employment_event}" <<SQL
BEGIN;
INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id, recorded_from
) VALUES (
    '${TENANT_ID}',
    '00000000-0000-7000-8000-000000000112',
    '00000000-0000-7000-8000-000000000101',
    TIMESTAMPTZ '2026-08-18 00:03:00+00'
);
SELECT record_audit_outbox_event(
    '${TENANT_ID}'::uuid,
    '00000000-0000-4000-8000-000000000145'::uuid,
    '00000000-0000-4000-8000-000000000155'::uuid,
    :'canonical_event',
    encode(digest(convert_to(:'canonical_event', 'UTF8'), 'sha256'), 'hex'),
    'orgmetra_domain_events'
);
INSERT INTO people_mutation_idempotency_record (
    tenant_record_id, people_mutation_idempotency_record_id, command_route,
    idempotency_key, command_digest, created_record_id
) VALUES (
    '${TENANT_ID}',
    '00000000-0000-7000-8000-000000000163',
    'employment-records',
    'idempotency-key-29xx',
    '${digest_two}',
    '00000000-0000-7000-8000-000000000112'
);
COMMIT;
SQL

second_counts="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT concat_ws(',',
    (SELECT count(*) FROM employment_record),
    (SELECT count(*) FROM audit_event_record),
    (SELECT count(*) FROM outbox_delivery_record),
    (SELECT count(*) FROM people_mutation_idempotency_record WHERE command_route = 'employment-records')
);
")"
if [[ "${second_counts}" != "2,2,2,2" ]]; then
    echo "different key did not persist a second employment command: ${second_counts}" >&2
    exit 1
fi

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v canonical_event="${assignment_event}" <<SQL
BEGIN;
INSERT INTO assignment_record (
    tenant_record_id, assignment_record_id, employment_record_id, person_record_id,
    position_record_id, allocation_ratio, effective_from, recorded_from
) VALUES (
    '${TENANT_ID}',
    '00000000-0000-7000-8000-000000000121',
    '00000000-0000-7000-8000-000000000111',
    '00000000-0000-7000-8000-000000000101',
    '00000000-0000-7000-8000-000000000108',
    1.0000,
    DATE '2026-08-18',
    TIMESTAMPTZ '2026-08-18 00:02:00+00'
);
SELECT record_audit_outbox_event(
    '${TENANT_ID}'::uuid,
    '00000000-0000-4000-8000-000000000143'::uuid,
    '00000000-0000-4000-8000-000000000153'::uuid,
    :'canonical_event',
    encode(digest(convert_to(:'canonical_event', 'UTF8'), 'sha256'), 'hex'),
    'orgmetra_domain_events'
);
INSERT INTO people_mutation_idempotency_record (
    tenant_record_id, people_mutation_idempotency_record_id, command_route,
    idempotency_key, command_digest, created_record_id
) VALUES (
    '${TENANT_ID}',
    '00000000-0000-7000-8000-000000000164',
    'assignment-records',
    'idempotency-key-17xx',
    '${digest_assignment}',
    '00000000-0000-7000-8000-000000000121'
);
COMMIT;
SQL

assignment_count="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "SELECT count(*) FROM assignment_record;")"
if [[ "${assignment_count}" != "1" ]]; then
    echo "assignment command under a distinct route was not persisted" >&2
    exit 1
fi

set +e
rollback_output="$({
    tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
    INSERT INTO people_mutation_idempotency_record (
        tenant_record_id, people_mutation_idempotency_record_id, command_route,
        idempotency_key, command_digest, created_record_id
    ) VALUES (
        '${TENANT_ID}',
        '00000000-0000-7000-8000-000000000165',
        'position-records',
        'idempotency-key-rollbackxx',
        '${digest_one}',
        '00000000-0000-7000-8000-000000000108'
    );
    RAISE EXCEPTION 'forced rollback of incomplete mutation';
END;
\$\$;
SQL
} 2>&1)"
rollback_status=$?
set -e
if [[ ${rollback_status} -eq 0 ]]; then
    echo "forced rollback unexpectedly committed" >&2
    exit 1
fi
if [[ "${rollback_output}" != *"forced rollback of incomplete mutation"* ]]; then
    echo "forced rollback failed for an unexpected reason: ${rollback_output}" >&2
    exit 1
fi
rollback_count="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*) FROM people_mutation_idempotency_record
WHERE idempotency_key = 'idempotency-key-rollbackxx';
")"
if [[ "${rollback_count}" != "0" ]]; then
    echo "rolled-back mutation left a false successful replay record" >&2
    exit 1
fi

PGOPTIONS="-c orgmetra.tenant_record_id=${FOREIGN_TENANT_ID}" psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO people_mutation_idempotency_record (
    tenant_record_id, people_mutation_idempotency_record_id, command_route,
    idempotency_key, command_digest, created_record_id
) VALUES (
    '${FOREIGN_TENANT_ID}',
    '00000000-0000-7000-8000-000000000166',
    'employment-records',
    'idempotency-key-17xx',
    '${digest_one}',
    '00000000-0000-7000-8000-000000000111'
);
SQL

assert_rejected "people_mutation_idempotency_key_check" \
  "INSERT INTO people_mutation_idempotency_record (tenant_record_id, people_mutation_idempotency_record_id, command_route, idempotency_key, command_digest, created_record_id) VALUES ('${TENANT_ID}', '00000000-0000-7000-8000-000000000167', 'employment-records', 'short', '${digest_one}', '00000000-0000-7000-8000-000000000111');"
assert_rejected "people_mutation_idempotency_route_check" \
  "INSERT INTO people_mutation_idempotency_record (tenant_record_id, people_mutation_idempotency_record_id, command_route, idempotency_key, command_digest, created_record_id) VALUES ('${TENANT_ID}', '00000000-0000-7000-8000-000000000168', 'person-records', 'idempotency-key-invalidxx', '${digest_one}', '00000000-0000-7000-8000-000000000111');"
assert_rejected "append-only relation cannot be updated or deleted" \
  "UPDATE people_mutation_idempotency_record SET command_digest = '${digest_two}' WHERE people_mutation_idempotency_record_id = '00000000-0000-7000-8000-000000000161';"
assert_rejected "append-only relation cannot be updated or deleted" \
  "DELETE FROM people_mutation_idempotency_record WHERE people_mutation_idempotency_record_id = '00000000-0000-7000-8000-000000000161';"
assert_rejected "people mutation idempotency records cannot be truncated" \
  "TRUNCATE TABLE people_mutation_idempotency_record;"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'orgmetra_people_idempotency_reader') THEN
        EXECUTE 'DROP OWNED BY orgmetra_people_idempotency_reader';
        EXECUTE 'DROP ROLE orgmetra_people_idempotency_reader';
    END IF;
END;
$$;
CREATE ROLE orgmetra_people_idempotency_reader NOLOGIN NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO orgmetra_people_idempotency_reader;
GRANT SELECT ON people_mutation_idempotency_record TO orgmetra_people_idempotency_reader;
SET ROLE orgmetra_people_idempotency_reader;

DO $$
DECLARE visible_count bigint;
BEGIN
    PERFORM set_config('orgmetra.tenant_record_id', '', false);
    SELECT count(*) INTO visible_count FROM people_mutation_idempotency_record;
    IF visible_count <> 0 THEN
        RAISE EXCEPTION 'missing tenant context exposed people mutation idempotency rows';
    END IF;
END;
$$;

SET orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
DO $$
DECLARE visible_count bigint;
BEGIN
    SELECT count(*) INTO visible_count FROM people_mutation_idempotency_record;
    IF visible_count <> 3 THEN
        RAISE EXCEPTION 'tenant alpha did not see its people mutation idempotency rows';
    END IF;
END;
$$;

SET orgmetra.tenant_record_id = '20000000-0000-7000-8000-000000000001';
DO $$
DECLARE visible_count bigint;
BEGIN
    SELECT count(*) INTO visible_count FROM people_mutation_idempotency_record;
    IF visible_count <> 1 THEN
        RAISE EXCEPTION 'foreign tenant context exposed another tenant people mutation idempotency rows';
    END IF;
END;
$$;

RESET ROLE;
SQL
