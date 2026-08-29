#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

# Migration 0008 is already applied in deployed databases. Prove the new
# withdrawal envelope is rejected by that legacy validator and accepted only
# after the forward repair migration is applied.
for migration in database/migrations/000{1..8}_*.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

withdrawal_validation() {
    psql "${DATABASE_URL}" -Atq <<'SQL'
WITH envelope AS (
    SELECT jsonb_build_object(
        'specversion', '1.0',
        'id', '00000000-0000-4000-8000-0000000000c1',
        'source', 'urn:orgmetra:talent_acquisition',
        'type', 'orgmetra.candidate.application_withdrawn',
        'subject', 'candidate_withdrawal_record:00000000-0000-4000-8000-0000000000c2',
        'time', '2026-08-21T09:10:00Z',
        'datacontenttype', 'application/json',
        'orgmetratenant', '10000000-0000-7000-8000-000000000001',
        'orgmetraactor', 'candidate:00000000-0000-4000-8000-0000000000c3',
        'orgmetrapurpose', 'candidate_withdrawal',
        'orgmetrareason', 'candidate_requested',
        'orgmetraevidence', 'candidate_withdrawal_evidence:00000000-0000-4000-8000-0000000000c4',
        'data', jsonb_build_object(
            'high_impact', false,
            'result_code', 'application_withdrawn',
            'evidence_version', 1,
            'identity_resolution_reference', 'identity_resolution:00000000-0000-4000-8000-0000000000c5',
            'identity_resolution_digest', repeat('a', 64),
            'withdrawal_evidence_digest', repeat('b', 64)
        )
    )::text AS canonical_event_json
), payload AS (
    SELECT
        canonical_event_json,
        encode(digest(convert_to(canonical_event_json, 'UTF8'), 'sha256'), 'hex')
            AS event_digest
    FROM envelope
)
SELECT public.validate_audit_event_envelope(
    canonical_event_json,
    '00000000-0000-4000-8000-0000000000c1'::uuid,
    '10000000-0000-7000-8000-000000000001'::uuid,
    event_digest
)
FROM payload;
SQL
}

legacy_result="$(withdrawal_validation)"
if [[ "${legacy_result}" != "f" ]]; then
    echo "legacy migration 0008 unexpectedly accepted a candidate withdrawal envelope: ${legacy_result}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -f database/migrations/0016_candidate_withdrawal_audit_envelope.sql

upgraded_result="$(withdrawal_validation)"
if [[ "${upgraded_result}" != "t" ]]; then
    echo "forward migration 0016 did not enable candidate withdrawal envelopes: ${upgraded_result}" >&2
    exit 1
fi

echo "candidate withdrawal migration upgrade contract passed"
