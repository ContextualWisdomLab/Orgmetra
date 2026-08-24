-- Harden authoritative Position lifecycle application against stale or forged
-- review snapshots.  Review evidence is accepted only when its exact canonical
-- JSON bytes are preserved and its value-minimized Position/Assignment digests
-- still match authoritative bitemporal truth at application time.

CREATE FUNCTION position_lifecycle_review_canonical_json(
    p_review_json text
)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
DECLARE
    payload jsonb;
    canonical_text text;
BEGIN
    BEGIN
        payload := p_review_json::jsonb;
    EXCEPTION WHEN others THEN
        RETURN NULL;
    END;

    IF pg_catalog.jsonb_typeof(payload) <> 'object' THEN
        RETURN NULL;
    END IF;

    SELECT '{' || pg_catalog.string_agg(
        pg_catalog.to_json(key_name)::text || ':' || key_value::text,
        ',' ORDER BY key_name COLLATE "C"
    ) || '}'
    INTO canonical_text
    FROM pg_catalog.jsonb_each(payload) AS entry(key_name, key_value);

    RETURN canonical_text;
END;
$$;

COMMENT ON FUNCTION position_lifecycle_review_canonical_json(text) IS
    'Returns the compact C-collation key-sorted JSON object representation required by Position lifecycle review evidence; malformed or non-object input returns NULL.';

CREATE FUNCTION position_lifecycle_position_snapshot_digest(
    p_tenant_record_id uuid,
    p_position_record_id uuid,
    p_effective_on date
)
RETURNS text
LANGUAGE sql
STABLE
STRICT
AS $$
    WITH current_snapshot AS (
        SELECT pg_catalog.jsonb_build_object(
            'effective_on', p_effective_on,
            'effective_from', version.effective_from,
            'effective_to', version.effective_to,
            'job_profile_id', position.job_profile_id::text,
            'organization_unit_id', position.organization_unit_id::text,
            'position_record_id', position.position_record_id::text,
            'position_record_version_id', version.position_record_version_id::text,
            'position_status_code', version.position_status_code
        ) AS payload
        FROM public.position_record AS position
        JOIN public.position_record_version AS version
          ON version.tenant_record_id = position.tenant_record_id
         AND version.position_record_id = position.position_record_id
        WHERE position.tenant_record_id = p_tenant_record_id
          AND position.position_record_id = p_position_record_id
          AND position.recorded_from <= pg_catalog.transaction_timestamp()
          AND (position.recorded_to IS NULL OR pg_catalog.transaction_timestamp() < position.recorded_to)
          AND version.recorded_from <= pg_catalog.transaction_timestamp()
          AND (version.recorded_to IS NULL OR pg_catalog.transaction_timestamp() < version.recorded_to)
          AND version.effective_from <= p_effective_on
          AND (version.effective_to IS NULL OR p_effective_on < version.effective_to)
    )
    SELECT pg_catalog.encode(
        public.digest(pg_catalog.convert_to(payload::text, 'UTF8'), 'sha256'),
        'hex'
    )
    FROM current_snapshot;
$$;

COMMENT ON FUNCTION position_lifecycle_position_snapshot_digest(uuid, uuid, date) IS
    'Returns a SHA-256 digest of the exact system-visible Position anchor/version truth at one business-effective date, or NULL when no authoritative Position snapshot exists.';

CREATE FUNCTION position_lifecycle_assignment_snapshot_digest(
    p_tenant_record_id uuid,
    p_position_record_id uuid,
    p_effective_on date
)
RETURNS text
LANGUAGE sql
STABLE
STRICT
AS $$
    WITH visible_assignments AS (
        SELECT assignment.assignment_record_id,
               assignment.allocation_ratio,
               assignment.effective_from,
               assignment.effective_to
        FROM public.assignment_record AS assignment
        WHERE assignment.tenant_record_id = p_tenant_record_id
          AND assignment.position_record_id = p_position_record_id
          AND assignment.recorded_from <= pg_catalog.transaction_timestamp()
          AND (assignment.recorded_to IS NULL OR pg_catalog.transaction_timestamp() < assignment.recorded_to)
          AND assignment.effective_from <= p_effective_on
          AND (assignment.effective_to IS NULL OR p_effective_on < assignment.effective_to)
    ), snapshot AS (
        SELECT pg_catalog.jsonb_build_object(
            'assignments', COALESCE(
                pg_catalog.jsonb_agg(
                    pg_catalog.jsonb_build_object(
                        'allocation_ratio', assignment.allocation_ratio::text,
                        'assignment_record_id', assignment.assignment_record_id::text,
                        'effective_from', assignment.effective_from,
                        'effective_to', assignment.effective_to
                    ) ORDER BY assignment.assignment_record_id
                ),
                '[]'::jsonb
            ),
            'effective_on', p_effective_on,
            'position_record_id', p_position_record_id::text
        ) AS payload
        FROM visible_assignments AS assignment
    )
    SELECT pg_catalog.encode(
        public.digest(pg_catalog.convert_to(payload::text, 'UTF8'), 'sha256'),
        'hex'
    )
    FROM snapshot;
$$;

COMMENT ON FUNCTION position_lifecycle_assignment_snapshot_digest(uuid, uuid, date) IS
    'Returns a SHA-256 digest of value-minimized system-visible Assignment occupancy truth for one Position at one business-effective date; an empty assignment set has a deterministic digest.';

-- Preserve the already-reviewed transition/shape validator as an internal stage,
-- then put canonical-byte and fresh-snapshot checks in front of every caller of
-- the public validation contract.
ALTER FUNCTION public.validate_position_lifecycle_review_evidence(
    text, text, uuid, uuid, text, text, date
) RENAME TO validate_position_lifecycle_review_evidence_v1_shape;

CREATE FUNCTION validate_position_lifecycle_review_evidence(
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
    review_payload jsonb;
    canonical_review text;
    expected_position_digest text;
    expected_assignment_digest text;
BEGIN
    canonical_review := public.position_lifecycle_review_canonical_json(
        p_canonical_review_json
    );
    IF canonical_review IS NULL
       OR canonical_review <> p_canonical_review_json THEN
        RETURN false;
    END IF;

    IF public.validate_position_lifecycle_review_evidence_v1_shape(
        p_canonical_review_json,
        p_review_digest,
        p_tenant_record_id,
        p_position_record_id,
        p_expected_current_status,
        p_expected_proposed_status,
        p_effective_on
    ) IS NOT TRUE THEN
        RETURN false;
    END IF;

    review_payload := p_canonical_review_json::jsonb;
    expected_position_digest := public.position_lifecycle_position_snapshot_digest(
        p_tenant_record_id,
        p_position_record_id,
        p_effective_on
    );
    expected_assignment_digest := public.position_lifecycle_assignment_snapshot_digest(
        p_tenant_record_id,
        p_position_record_id,
        p_effective_on
    );

    IF expected_position_digest IS NULL
       OR review_payload ->> 'position_snapshot_digest_sha256'
          IS DISTINCT FROM expected_position_digest
       OR review_payload ->> 'assignment_snapshot_digest_sha256'
          IS DISTINCT FROM expected_assignment_digest THEN
        RETURN false;
    END IF;

    RETURN true;
END;
$$;

COMMENT ON FUNCTION validate_position_lifecycle_review_evidence(text, text, uuid, uuid, text, text, date) IS
    'Validates exact canonical v1 review bytes, digest, tenant/Position/status/effective scope, allowed transition graph, human-review chronology, and fresh authoritative Position/Assignment snapshot digests without granting mutation authority.';

COMMENT ON FUNCTION validate_position_lifecycle_review_evidence_v1_shape(text, text, uuid, uuid, text, text, date) IS
    'Internal v1 review shape/transition validator retained beneath the canonical-byte and fresh-snapshot validation boundary.';

-- High-impact lifecycle mutation must never inherit PostgreSQL default PUBLIC
-- function execution. Deployment grants are an explicit authority decision.
REVOKE ALL ON FUNCTION public.apply_position_lifecycle_change(
    uuid, uuid, uuid, uuid, uuid, text, text, text, uuid, uuid
) FROM PUBLIC;
