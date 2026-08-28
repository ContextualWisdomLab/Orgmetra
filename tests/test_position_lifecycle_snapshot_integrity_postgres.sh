#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"

migration="database/migrations/0025_position_lifecycle_snapshot_hardening.sql"
test -f "$migration"
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$migration" >/dev/null

TENANT="0198a412-8000-7000-8000-000000000101"
POSITION="0198a412-8000-7000-8000-000000000104"
CURRENT_VERSION="0198a412-8000-7000-8000-000000000106"
SUCCESSOR="0198a412-8000-7000-8000-000000000121"
APPLICATION="0198a412-8000-7000-8000-000000000122"
AUDIT="0198a412-8000-7000-8000-000000000123"
OUTBOX="0198a412-8000-7000-8000-000000000124"
REVIEW_REF="f0ec646a-4f21-4e6c-87e1-7a51c4545534"
REQUESTER="actor:9d5a177e-79e9-4022-8f35-b2408ec5a503"
REVIEWER="actor:6aacb560-ec5d-41d7-94a5-27cf95438b1b"
APPLIER="actor:faefac04-52e8-43d2-aa54-d9046238733f"

# The authoritative database snapshot digests must be available to the review
# producer and to the application guard. Their absence is itself fail-closed.
POSITION_DIGEST="$(psql "$DATABASE_URL" -At -v ON_ERROR_STOP=1 -v tenant="$TENANT" -v position="$POSITION" <<'SQL'
SELECT public.position_lifecycle_position_snapshot_digest(
    :'tenant', :'position', DATE '2026-09-15'
);
SQL
)"
ASSIGNMENT_DIGEST="$(psql "$DATABASE_URL" -At -v ON_ERROR_STOP=1 -v tenant="$TENANT" -v position="$POSITION" <<'SQL'
SELECT public.position_lifecycle_assignment_snapshot_digest(
    :'tenant', :'position', DATE '2026-09-15'
);
SQL
)"
test "$POSITION_DIGEST" != ""
test "$ASSIGNMENT_DIGEST" != ""

# Exact parent-package canonical JSON has sorted keys and compact separators.
REVIEW_JSON="$(python - <<PY
import json
print(json.dumps({
    "assignment_snapshot_digest_sha256": "${ASSIGNMENT_DIGEST}",
    "current_status_code": "frozen",
    "decision_authority": "human_review_only",
    "effective_on": "2026-09-15",
    "evidence_version": 1,
    "mutation_state": "not_authorized_to_apply",
    "next_action": "Re-resolve tenant-qualified Position and Assignment truth at the requested business/system coordinate; require authoritative actor separation, reviewed evidence, staffing safety, and immutable audit/outbox before any lifecycle mutation.",
    "position_lifecycle_change_reference": "${REVIEW_REF}",
    "position_record_id": "${POSITION}",
    "position_snapshot_digest_sha256": "${POSITION_DIGEST}",
    "proposed_status_code": "open",
    "reason_code": "position_reactivation",
    "recorded_at": "2026-08-24T14:00:00Z",
    "requester_actor_reference": "${REQUESTER}",
    "review_outcome_code": "approved_for_authoritative_resolution",
    "review_state": "human_reviewed",
    "reviewed_at": "2026-08-24T13:55:00Z",
    "reviewer_actor_reference": "${REVIEWER}",
    "scope_verification_state": "requires_authoritative_resolution",
    "tenant_record_id": "${TENANT}",
}, separators=(",", ":"), sort_keys=True, ensure_ascii=False))
PY
)"
REVIEW_DIGEST="$(printf '%s' "$REVIEW_JSON" | sha256sum | awk '{print $1}')"

canonicalized="$(psql "$DATABASE_URL" -At -v ON_ERROR_STOP=1 -v review_json="$REVIEW_JSON" <<'SQL'
SELECT public.position_lifecycle_review_canonical_json(:'review_json');
SQL
)"
test "$canonicalized" = "$REVIEW_JSON"

valid_accepted="$(psql "$DATABASE_URL" -At -v ON_ERROR_STOP=1 \
  -v review_json="$REVIEW_JSON" -v review_digest="$REVIEW_DIGEST" \
  -v tenant="$TENANT" -v position="$POSITION" <<'SQL'
SELECT public.validate_position_lifecycle_review_evidence(
    :'review_json', :'review_digest', :'tenant', :'position',
    'frozen', 'open', DATE '2026-09-15'
);
SQL
)"
test "$valid_accepted" = "t"

# A semantically equivalent but noncanonical representation must not become
# durable review evidence merely because a caller recomputed its SHA-256.
NONCANONICAL_JSON="$(printf '%s' "$REVIEW_JSON" | python -c 'import json,sys; print(json.dumps(json.load(sys.stdin), sort_keys=False, indent=1, ensure_ascii=False))')"
NONCANONICAL_DIGEST="$(printf '%s' "$NONCANONICAL_JSON" | sha256sum | awk '{print $1}')"
noncanonical_accepted="$(psql "$DATABASE_URL" -At -v ON_ERROR_STOP=1 \
  -v review_json="$NONCANONICAL_JSON" -v review_digest="$NONCANONICAL_DIGEST" \
  -v tenant="$TENANT" -v position="$POSITION" <<'SQL'
SELECT public.validate_position_lifecycle_review_evidence(
    :'review_json', :'review_digest', :'tenant', :'position',
    'frozen', 'open', DATE '2026-09-15'
);
SQL
)"
test "$noncanonical_accepted" = "f"

# A caller cannot substitute arbitrary but syntactically valid snapshot hashes.
FORGED_JSON="$(printf '%s' "$REVIEW_JSON" | python -c 'import json,sys; d=json.load(sys.stdin); d["position_snapshot_digest_sha256"]="0"*64; print(json.dumps(d,separators=(",",":"),sort_keys=True,ensure_ascii=False))')"
FORGED_DIGEST="$(printf '%s' "$FORGED_JSON" | sha256sum | awk '{print $1}')"
if psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -v tenant="$TENANT" -v position="$POSITION" -v current_version="$CURRENT_VERSION" \
  -v successor="$SUCCESSOR" -v application="$APPLICATION" \
  -v review_json="$FORGED_JSON" -v review_digest="$FORGED_DIGEST" \
  -v applier="$APPLIER" -v audit="$AUDIT" -v outbox="$OUTBOX" <<'SQL' >/dev/null 2>&1
SELECT public.apply_position_lifecycle_change(
    :'tenant', :'position', :'current_version', :'successor', :'application',
    :'review_json', :'review_digest', :'applier', :'audit', :'outbox'
);
SQL
then
  echo "forged lifecycle snapshot evidence was applied" >&2
  exit 1
fi

# The exact fresh snapshot evidence must still be usable through the authoritative
# application boundary after the forged attempt rolls back atomically.
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

applied_status="$(psql "$DATABASE_URL" -At -v ON_ERROR_STOP=1 \
  -v tenant="$TENANT" -v successor="$SUCCESSOR" <<'SQL'
SELECT position_status_code
FROM position_record_version
WHERE tenant_record_id = :'tenant'
  AND position_record_version_id = :'successor'
  AND recorded_to IS NULL;
SQL
)"
test "$applied_status" = "open"

# The high-impact mutation function must never be executable through PostgreSQL's
# default PUBLIC function privilege; deployment must grant it deliberately.
public_execute="$(psql "$DATABASE_URL" -At -v ON_ERROR_STOP=1 <<'SQL'
SELECT EXISTS (
    SELECT 1
    FROM pg_proc AS procedure
    CROSS JOIN LATERAL aclexplode(
        coalesce(procedure.proacl, acldefault('f', procedure.proowner))
    ) AS privilege
    WHERE procedure.oid = 'public.apply_position_lifecycle_change(uuid,uuid,uuid,uuid,uuid,text,text,text,uuid,uuid)'::regprocedure
      AND privilege.grantee = 0
      AND privilege.privilege_type = 'EXECUTE'
);
SQL
)"
test "$public_execute" = "f"

search_path_contract="$(psql "$DATABASE_URL" -At -v ON_ERROR_STOP=1 <<'SQL'
SELECT count(*)
FROM pg_catalog.pg_proc AS procedure_record
WHERE procedure_record.oid IN (
    'public.validate_position_lifecycle_review_evidence_v1_shape(text,text,uuid,uuid,text,text,date)'::regprocedure,
    'public.validate_position_lifecycle_review_evidence(text,text,uuid,uuid,text,text,date)'::regprocedure,
    'public.position_lifecycle_review_canonical_json(text)'::regprocedure,
    'public.position_lifecycle_position_snapshot_digest(uuid,uuid,date)'::regprocedure,
    'public.position_lifecycle_assignment_snapshot_digest(uuid,uuid,date)'::regprocedure,
    'public.protect_position_lifecycle_application_history()'::regprocedure,
    'public.protect_position_version_history_after_lifecycle_support()'::regprocedure,
    'public.validate_position_lifecycle_application_audit()'::regprocedure,
    'public.validate_position_lifecycle_application_successor()'::regprocedure,
    'public.reject_position_lifecycle_history_truncate()'::regprocedure,
    'public.apply_position_lifecycle_change(uuid,uuid,uuid,uuid,uuid,text,text,text,uuid,uuid)'::regprocedure
)
AND procedure_record.proconfig @> ARRAY['search_path=pg_catalog, public, pg_temp']::text[];
SQL
)"
test "$search_path_contract" = "11"

echo "position lifecycle snapshot integrity: PASS"
