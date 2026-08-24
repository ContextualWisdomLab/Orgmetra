-- Strengthen the Position lifecycle application boundary so a caller cannot
-- manufacture otherwise well-shaped review JSON for a no-op or forbidden state
-- transition and recompute its SHA-256.  The authoritative persistence boundary
-- independently enforces the same transition graph as the reviewed evidence type.

CREATE OR REPLACE FUNCTION validate_position_lifecycle_review_evidence(
    p_canonical_review_json text,
    p_review_digest text,
    p_tenant_record_id uuid,
    p_position_record_id uuid,
    p_expected_current_status text,
    p_expected_proposed_status text,
    p_effective_on date
)
RETURNS boolean
LANGUAGE plpgsql
STABLE
STRICT
AS $$
DECLARE
    review_json json;
    review_payload jsonb;
    review_keys text[];
    key_count integer;
    reviewed_at timestamptz;
    review_recorded_at timestamptz;
    expected_keys constant text[] := ARRAY[
        'assignment_snapshot_digest_sha256',
        'current_status_code',
        'decision_authority',
        'effective_on',
        'evidence_version',
        'mutation_state',
        'next_action',
        'position_lifecycle_change_reference',
        'position_record_id',
        'position_snapshot_digest_sha256',
        'proposed_status_code',
        'reason_code',
        'recorded_at',
        'requester_actor_reference',
        'review_outcome_code',
        'review_state',
        'reviewed_at',
        'reviewer_actor_reference',
        'scope_verification_state',
        'tenant_record_id'
    ];
BEGIN
    IF p_review_digest !~ '^[0-9a-f]{64}$'
       OR encode(
            public.digest(pg_catalog.convert_to(p_canonical_review_json, 'UTF8'), 'sha256'),
            'hex'
          ) <> p_review_digest THEN
        RETURN false;
    END IF;

    BEGIN
        review_json := p_canonical_review_json::json;
        review_payload := p_canonical_review_json::jsonb;
    EXCEPTION WHEN others THEN
        RETURN false;
    END;

    IF pg_catalog.jsonb_typeof(review_payload) <> 'object' THEN
        RETURN false;
    END IF;

    SELECT count(*), array_agg(key ORDER BY key)
    INTO key_count, review_keys
    FROM pg_catalog.json_object_keys(review_json) AS key_set(key);
    IF key_count <> 20 OR review_keys <> expected_keys THEN
        RETURN false;
    END IF;

    IF review_payload ->> 'tenant_record_id' <> p_tenant_record_id::text
       OR review_payload ->> 'position_record_id' <> p_position_record_id::text
       OR review_payload ->> 'current_status_code' <> p_expected_current_status
       OR review_payload ->> 'proposed_status_code' <> p_expected_proposed_status
       OR review_payload ->> 'effective_on' <> p_effective_on::text
       OR review_payload ->> 'decision_authority' <> 'human_review_only'
       OR review_payload ->> 'mutation_state' <> 'not_authorized_to_apply'
       OR review_payload ->> 'review_outcome_code' <> 'approved_for_authoritative_resolution'
       OR review_payload ->> 'review_state' <> 'human_reviewed'
       OR review_payload ->> 'scope_verification_state' <> 'requires_authoritative_resolution'
       OR review_payload ->> 'evidence_version' <> '1'
       OR review_payload ->> 'position_snapshot_digest_sha256' !~ '^[0-9a-f]{64}$'
       OR review_payload ->> 'assignment_snapshot_digest_sha256' !~ '^[0-9a-f]{64}$'
       OR review_payload ->> 'position_lifecycle_change_reference'
          !~ '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
       OR review_payload ->> 'requester_actor_reference'
          !~ '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
       OR review_payload ->> 'reviewer_actor_reference'
          !~ '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
       OR review_payload ->> 'requester_actor_reference' = review_payload ->> 'reviewer_actor_reference' THEN
        RETURN false;
    END IF;

    IF NOT (
        (p_expected_current_status = 'open' AND p_expected_proposed_status IN ('active', 'frozen', 'closed', 'abolished'))
        OR (p_expected_current_status = 'active' AND p_expected_proposed_status IN ('frozen', 'closed', 'abolished'))
        OR (p_expected_current_status = 'frozen' AND p_expected_proposed_status IN ('open', 'active', 'closed', 'abolished'))
        OR (p_expected_current_status = 'closed' AND p_expected_proposed_status IN ('open', 'abolished'))
    ) THEN
        RETURN false;
    END IF;

    IF p_expected_proposed_status IN ('active', 'open')
       AND review_payload ->> 'reason_code' <> 'position_reactivation' THEN
        RETURN false;
    ELSIF p_expected_proposed_status = 'frozen'
       AND review_payload ->> 'reason_code' <> 'temporary_freeze' THEN
        RETURN false;
    ELSIF p_expected_proposed_status = 'closed'
       AND review_payload ->> 'reason_code' <> 'position_closure' THEN
        RETURN false;
    ELSIF p_expected_proposed_status = 'abolished'
       AND review_payload ->> 'reason_code' <> 'position_abolition' THEN
        RETURN false;
    END IF;

    BEGIN
        reviewed_at := (review_payload ->> 'reviewed_at')::timestamptz;
        review_recorded_at := (review_payload ->> 'recorded_at')::timestamptz;
    EXCEPTION WHEN others THEN
        RETURN false;
    END;
    IF reviewed_at IS NULL
       OR review_recorded_at IS NULL
       OR reviewed_at > review_recorded_at
       OR review_recorded_at > pg_catalog.transaction_timestamp() THEN
        RETURN false;
    END IF;

    RETURN true;
END;
$$;

COMMENT ON FUNCTION validate_position_lifecycle_review_evidence(text, text, uuid, uuid, text, text, date) IS
    'Validates exact v1 Position lifecycle review shape, digest, tenant/Position/status/effective scope, allowed non-no-op transition graph, human approval state, and chronology without granting mutation authority.';
