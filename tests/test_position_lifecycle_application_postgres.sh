#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"

migration="database/migrations/0023_position_lifecycle_application.sql"
test -f "$migration"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql >/dev/null
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql >/dev/null
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/0003_audit_outbox_persistence.sql >/dev/null
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$migration" >/dev/null

TENANT="0198a412-8000-7000-8000-000000000101"
ORG="0198a412-8000-7000-8000-000000000102"
JOB="0198a412-8000-7000-8000-000000000103"
POSITION="0198a412-8000-7000-8000-000000000104"
CURRENT_VERSION="0198a412-8000-7000-8000-000000000105"
SUCCESSOR="0198a412-8000-7000-8000-000000000106"
APPLICATION="0198a412-8000-7000-8000-000000000107"
AUDIT="0198a412-8000-7000-8000-000000000108"
OUTBOX="0198a412-8000-7000-8000-000000000109"
REVIEW_REF="a0e89c71-41c1-4c63-935c-8569d83f7901"
REQUESTER="actor:9d5a177e-79e9-4022-8f35-b2408ec5a503"
REVIEWER="actor:6aacb560-ec5d-41d7-94a5-27cf95438b1b"
APPLIER="actor:faefac04-52e8-43d2-aa54-d9046238733f"
POSITION_DIGEST="$(printf 'position-snapshot' | sha256sum | awk '{print $1}')"
ASSIGNMENT_DIGEST="$(printf 'assignment-snapshot' | sha256sum | awk '{print $1}')"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -v tenant="$TENANT" -v org="$ORG" -v job="$JOB" -v position="$POSITION" -v current_version="$CURRENT_VERSION" <<'SQL' >/dev/null
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES (:'tenant', 'tenant:lifecycle_test');
INSERT INTO organization_unit (tenant_record_id, organization_unit_id)
VALUES (:'tenant', :'org');
INSERT INTO job_profile (tenant_record_id, job_profile_id)
VALUES (:'tenant', :'job');
INSERT INTO position_record (
    tenant_record_id, position_record_id, organization_unit_id, job_profile_id
) VALUES (:'tenant', :'position', :'org', :'job');
INSERT INTO position_record_version (
    tenant_record_id, position_record_version_id, position_record_id,
    position_status_code, effective_from
) VALUES (:'tenant', :'current_version', :'position', 'open', DATE '2026-01-01');
SQL

make_review() {
  local outcome="$1"
  local current="$2"
  local proposed="$3"
  local reason="$4"
  psql "$DATABASE_URL" -At -v ON_ERROR_STOP=1 \
    -v tenant="$TENANT" -v position="$POSITION" -v review_ref="$REVIEW_REF" \
    -v requester="$REQUESTER" -v reviewer="$REVIEWER" \
    -v position_digest="$POSITION_DIGEST" -v assignment_digest="$ASSIGNMENT_DIGEST" \
    -v outcome="$outcome" -v current="$current" -v proposed="$proposed" -v reason="$reason" <<'SQL'
SELECT jsonb_build_object(
    'assignment_snapshot_digest_sha256', :'assignment_digest',
    'current_status_code', :'current',
    'decision_authority', 'human_review_only',
    'effective_on', '2026-09-01',
    'evidence_version', 1,
    'mutation_state', 'not_authorized_to_apply',
    'next_action', CASE WHEN :'outcome' = 'rejected'
        THEN 'Do not apply the proposed Position lifecycle change.'
        ELSE 'Re-resolve tenant-qualified Position and Assignment truth at the requested business/system coordinate; require authoritative actor separation, reviewed evidence, staffing safety, and immutable audit/outbox before any lifecycle mutation.' END,
    'position_lifecycle_change_reference', :'review_ref',
    'position_record_id', :'position',
    'position_snapshot_digest_sha256', :'position_digest',
    'proposed_status_code', :'proposed',
    'reason_code', :'reason',
    'recorded_at', '2026-08-24T14:00:00Z',
    'requester_actor_reference', :'requester',
    'review_outcome_code', :'outcome',
    'review_state', 'human_reviewed',
    'reviewed_at', '2026-08-24T13:55:00Z',
    'reviewer_actor_reference', :'reviewer',
    'scope_verification_state', 'requires_authoritative_resolution',
    'tenant_record_id', :'tenant'
)::text;
SQL
}

REVIEW_JSON="$(make_review approved_for_authoritative_resolution open frozen temporary_freeze)"
REVIEW_DIGEST="$(printf '%s' "$REVIEW_JSON" | sha256sum | awk '{print $1}')"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -v tenant="$TENANT" -v position="$POSITION" -v current_version="$CURRENT_VERSION" \
  -v successor="$SUCCESSOR" -v application="$APPLICATION" \
  -v review_json="$REVIEW_JSON" -v review_digest="$REVIEW_DIGEST" \
  -v applier="$APPLIER" -v audit="$AUDIT" -v outbox="$OUTBOX" <<'SQL' >/dev/null
SELECT public.apply_position_lifecycle_change(
    :'tenant', :'position', :'current_version', :'successor', :'application',
    :'review_json', :'review_digest', :'applier', :'audit', :'outbox'
);
SQL

status_rows="$(psql "$DATABASE_URL" -At -v ON_ERROR_STOP=1 -v tenant="$TENANT" -v position="$POSITION" <<'SQL'
SELECT string_agg(position_status_code || ':' || effective_from::text || ':' || coalesce(effective_to::text, 'infinity'), ',' ORDER BY effective_from)
FROM position_record_version
WHERE tenant_record_id = :'tenant'
  AND position_record_id = :'position'
  AND recorded_to IS NULL;
SQL
)"
test "$status_rows" = "open:2026-01-01:2026-09-01,frozen:2026-09-01:infinity"

application_count="$(psql "$DATABASE_URL" -At -v ON_ERROR_STOP=1 -v tenant="$TENANT" -v application="$APPLICATION" <<'SQL'
SELECT count(*) FROM position_lifecycle_application_record
WHERE tenant_record_id = :'tenant'
  AND position_lifecycle_application_record_id = :'application'
  AND application_state = 'applied_after_human_review';
SQL
)"
test "$application_count" = "1"

# Rejected review evidence must not mutate Position truth.
REJECTED_REVIEW="$(make_review rejected frozen closed position_closure)"
REJECTED_DIGEST="$(printf '%s' "$REJECTED_REVIEW" | sha256sum | awk '{print $1}')"
if psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -v tenant="$TENANT" -v position="$POSITION" -v current_version="$SUCCESSOR" \
  -v successor="0198a412-8000-7000-8000-00000000010a" \
  -v application="0198a412-8000-7000-8000-00000000010b" \
  -v review_json="$REJECTED_REVIEW" -v review_digest="$REJECTED_DIGEST" \
  -v applier="$APPLIER" -v audit="0198a412-8000-7000-8000-00000000010c" \
  -v outbox="0198a412-8000-7000-8000-00000000010d" <<'SQL' >/dev/null 2>&1
SELECT public.apply_position_lifecycle_change(
    :'tenant', :'position', :'current_version', :'successor', :'application',
    :'review_json', :'review_digest', :'applier', :'audit', :'outbox'
);
SQL
then
  echo "rejected lifecycle review was applied" >&2
  exit 1
fi

# Closing/abolishing a seat with a live assignment crossing the effective date must fail.
EMPLOYMENT="0198a412-8000-7000-8000-00000000010e"
PERSON="0198a412-8000-7000-8000-00000000010f"
ASSIGNMENT="0198a412-8000-7000-8000-000000000110"
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -v tenant="$TENANT" -v person="$PERSON" -v employment="$EMPLOYMENT" -v assignment="$ASSIGNMENT" -v position="$POSITION" <<'SQL' >/dev/null
INSERT INTO person_record (tenant_record_id, person_record_id) VALUES (:'tenant', :'person');
INSERT INTO employment_record (tenant_record_id, employment_record_id, person_record_id) VALUES (:'tenant', :'employment', :'person');
INSERT INTO assignment_record (
    tenant_record_id, assignment_record_id, employment_record_id, person_record_id,
    position_record_id, allocation_ratio, effective_from
) VALUES (:'tenant', :'assignment', :'employment', :'person', :'position', 1.0000, DATE '2026-08-01');
SQL

CLOSE_REVIEW="$(make_review approved_for_authoritative_resolution frozen closed position_closure)"
CLOSE_DIGEST="$(printf '%s' "$CLOSE_REVIEW" | sha256sum | awk '{print $1}')"
if psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -v tenant="$TENANT" -v position="$POSITION" -v current_version="$SUCCESSOR" \
  -v successor="0198a412-8000-7000-8000-000000000111" \
  -v application="0198a412-8000-7000-8000-000000000112" \
  -v review_json="$CLOSE_REVIEW" -v review_digest="$CLOSE_DIGEST" \
  -v applier="$APPLIER" -v audit="0198a412-8000-7000-8000-000000000113" \
  -v outbox="0198a412-8000-7000-8000-000000000114" <<'SQL' >/dev/null 2>&1
SELECT public.apply_position_lifecycle_change(
    :'tenant', :'position', :'current_version', :'successor', :'application',
    :'review_json', :'review_digest', :'applier', :'audit', :'outbox'
);
SQL
then
  echo "position close was applied across a live Assignment" >&2
  exit 1
fi

# Direct history rewrite/delete must remain blocked.
if psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -v tenant="$TENANT" -v position="$POSITION" <<'SQL' >/dev/null 2>&1
UPDATE position_record_version
SET position_status_code = 'closed'
WHERE tenant_record_id = :'tenant' AND position_record_id = :'position' AND recorded_to IS NULL;
SQL
then
  echo "position version history was rewritten directly" >&2
  exit 1
fi

if psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -v tenant="$TENANT" -v application="$APPLICATION" <<'SQL' >/dev/null 2>&1
DELETE FROM position_lifecycle_application_record
WHERE tenant_record_id = :'tenant' AND position_lifecycle_application_record_id = :'application';
SQL
then
  echo "position lifecycle application evidence was deleted" >&2
  exit 1
fi

# Both owned relations must be forced-RLS.
force_rls="$(psql "$DATABASE_URL" -At -v ON_ERROR_STOP=1 <<'SQL'
SELECT string_agg(relname || ':' || relforcerowsecurity::text, ',' ORDER BY relname)
FROM pg_class
WHERE relname IN ('position_record_version', 'position_lifecycle_application_record');
SQL
)"
test "$force_rls" = "position_lifecycle_application_record:true,position_record_version:true"

echo "position lifecycle application persistence: PASS"
