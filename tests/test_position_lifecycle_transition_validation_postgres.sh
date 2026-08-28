#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql >/dev/null
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql >/dev/null
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/0003_audit_outbox_persistence.sql >/dev/null
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/0023_position_lifecycle_application.sql >/dev/null
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/0024_position_lifecycle_transition_hardening.sql >/dev/null

TENANT="0198a412-8000-7000-8000-000000000101"
POSITION="0198a412-8000-7000-8000-000000000104"
REVIEW_REF="a0e89c71-41c1-4c63-935c-8569d83f7901"
REQUESTER="actor:9d5a177e-79e9-4022-8f35-b2408ec5a503"
REVIEWER="actor:6aacb560-ec5d-41d7-94a5-27cf95438b1b"
POSITION_DIGEST="$(printf 'position-snapshot' | sha256sum | awk '{print $1}')"
ASSIGNMENT_DIGEST="$(printf 'assignment-snapshot' | sha256sum | awk '{print $1}')"

review_json="$(psql "$DATABASE_URL" -At -v ON_ERROR_STOP=1 \
  -v tenant="$TENANT" -v position="$POSITION" -v review_ref="$REVIEW_REF" \
  -v requester="$REQUESTER" -v reviewer="$REVIEWER" \
  -v position_digest="$POSITION_DIGEST" -v assignment_digest="$ASSIGNMENT_DIGEST" <<'SQL'
SELECT jsonb_build_object(
    'assignment_snapshot_digest_sha256', :'assignment_digest',
    'current_status_code', 'frozen',
    'decision_authority', 'human_review_only',
    'effective_on', '2026-09-01',
    'evidence_version', 1,
    'mutation_state', 'not_authorized_to_apply',
    'next_action', 'Re-resolve tenant-qualified Position and Assignment truth at the requested business/system coordinate; require authoritative actor separation, reviewed evidence, staffing safety, and immutable audit/outbox before any lifecycle mutation.',
    'position_lifecycle_change_reference', :'review_ref',
    'position_record_id', :'position',
    'position_snapshot_digest_sha256', :'position_digest',
    'proposed_status_code', 'frozen',
    'reason_code', 'temporary_freeze',
    'recorded_at', '2026-08-24T14:00:00Z',
    'requester_actor_reference', :'requester',
    'review_outcome_code', 'approved_for_authoritative_resolution',
    'review_state', 'human_reviewed',
    'reviewed_at', '2026-08-24T13:55:00Z',
    'reviewer_actor_reference', :'reviewer',
    'scope_verification_state', 'requires_authoritative_resolution',
    'tenant_record_id', :'tenant'
)::text;
SQL
)"
review_digest="$(printf '%s' "$review_json" | sha256sum | awk '{print $1}')"

accepted="$(psql "$DATABASE_URL" -At -v ON_ERROR_STOP=1 \
  -v review_json="$review_json" -v review_digest="$review_digest" \
  -v tenant="$TENANT" -v position="$POSITION" <<'SQL'
SELECT public.validate_position_lifecycle_review_evidence(
    :'review_json', :'review_digest', :'tenant', :'position',
    'frozen', 'frozen', DATE '2026-09-01'
);
SQL
)"

test "$accepted" = "f"
echo "position lifecycle transition validation: PASS"
