-- Harden the reviewed Organization hierarchy application boundary so a
-- successor never points at a proposed parent that disappears during the
-- successor's effective interval, and attribute emitted hierarchy events to
-- the organization_core owner rather than people_api.

CREATE OR REPLACE FUNCTION apply_organization_hierarchy_change(
    p_tenant_record_id uuid,
    p_organization_unit_id uuid,
    p_expected_predecessor_version_id uuid,
    p_successor_version_id uuid,
    p_application_record_id uuid,
    p_canonical_review_json text,
    p_review_digest text,
    p_applied_by_actor_reference text,
    p_audit_event_record_id uuid,
    p_outbox_delivery_record_id uuid
)
RETURNS void
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    review_payload jsonb;
    predecessor organization_unit_version%ROWTYPE;
    preserved_version_id uuid;
    current_parent_id uuid;
    proposed_parent_id uuid;
    review_reference uuid;
    requester text;
    reviewer text;
    reason text;
    effective_on date;
    review_recorded_at timestamptz;
    expected_unit_digest text;
    expected_hierarchy_digest text;
    parent_gap_found boolean;
    cycle_found boolean;
    event_json text;
    event_digest text;
BEGIN
    IF public.current_tenant_record_id() IS DISTINCT FROM p_tenant_record_id THEN
        RAISE EXCEPTION 'organization hierarchy application tenant context does not match the request'
            USING ERRCODE = '42501';
    END IF;

    IF public.is_operational_uuid(p_tenant_record_id) IS NOT TRUE
       OR public.is_operational_uuid(p_organization_unit_id) IS NOT TRUE
       OR public.is_operational_uuid(p_expected_predecessor_version_id) IS NOT TRUE
       OR public.is_operational_uuid(p_successor_version_id) IS NOT TRUE
       OR public.is_operational_uuid(p_application_record_id) IS NOT TRUE
       OR public.is_operational_uuid(p_audit_event_record_id) IS NOT TRUE
       OR public.is_operational_uuid(p_outbox_delivery_record_id) IS NOT TRUE THEN
        RAISE EXCEPTION 'organization hierarchy application requires operational UUID identities'
            USING ERRCODE = '23514';
    END IF;
    IF p_applied_by_actor_reference
       !~ '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' THEN
        RAISE EXCEPTION 'organization hierarchy applier must be a pseudonymous actor UUIDv4 correlation'
            USING ERRCODE = '23514';
    END IF;

    BEGIN
        review_payload := p_canonical_review_json::jsonb;
        effective_on := (review_payload ->> 'effective_on')::date;
        requester := review_payload ->> 'requester_reference';
        reviewer := review_payload ->> 'reviewer_reference';
        reason := review_payload ->> 'reason_code';
        review_recorded_at := (review_payload ->> 'recorded_at')::timestamptz;
        review_reference := substring(
            review_payload ->> 'organization_hierarchy_change_reference'
            FROM length('organization_hierarchy_change:') + 1
        )::uuid;
        current_parent_id := CASE
            WHEN review_payload -> 'current_parent_organization_unit_reference' = 'null'::jsonb THEN NULL
            ELSE substring(
                review_payload ->> 'current_parent_organization_unit_reference'
                FROM length('organization_unit:') + 1
            )::uuid
        END;
        proposed_parent_id := CASE
            WHEN review_payload -> 'proposed_parent_organization_unit_reference' = 'null'::jsonb THEN NULL
            ELSE substring(
                review_payload ->> 'proposed_parent_organization_unit_reference'
                FROM length('organization_unit:') + 1
            )::uuid
        END;
    EXCEPTION WHEN others THEN
        RAISE EXCEPTION 'organization hierarchy review evidence cannot be parsed safely'
            USING ERRCODE = '23514';
    END;

    IF reviewer = p_applied_by_actor_reference THEN
        RAISE EXCEPTION 'organization hierarchy reviewer and applier must be distinct actors'
            USING ERRCODE = '23514';
    END IF;

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(
            'orgmetra_organization_hierarchy:' || p_tenant_record_id::text,
            0
        )
    );

    PERFORM 1
    FROM organization_unit
    WHERE tenant_record_id = p_tenant_record_id
      AND organization_unit_id = p_organization_unit_id
      AND recorded_from <= pg_catalog.transaction_timestamp()
      AND (recorded_to IS NULL OR pg_catalog.transaction_timestamp() < recorded_to)
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Organization Unit is not current in the tenant'
            USING ERRCODE = '23503';
    END IF;

    SELECT version.*
    INTO predecessor
    FROM organization_unit_version AS version
    WHERE version.tenant_record_id = p_tenant_record_id
      AND version.organization_unit_id = p_organization_unit_id
      AND version.recorded_from <= pg_catalog.transaction_timestamp()
      AND (version.recorded_to IS NULL OR pg_catalog.transaction_timestamp() < version.recorded_to)
      AND version.effective_from <= effective_on
      AND (version.effective_to IS NULL OR effective_on < version.effective_to)
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'no current OrganizationUnitVersion covers the requested effective date'
            USING ERRCODE = '23503';
    END IF;
    IF predecessor.organization_unit_version_id <> p_expected_predecessor_version_id
       OR predecessor.parent_organization_unit_id IS DISTINCT FROM current_parent_id THEN
        RAISE EXCEPTION 'reviewed Organization Unit parent state is stale at authoritative application time'
            USING ERRCODE = '40001';
    END IF;

    IF NOT validate_organization_hierarchy_change_review_evidence(
        p_canonical_review_json,
        p_review_digest,
        p_tenant_record_id,
        p_organization_unit_id,
        effective_on
    ) THEN
        RAISE EXCEPTION 'organization hierarchy review evidence is invalid or out of scope'
            USING ERRCODE = '23514';
    END IF;

    IF proposed_parent_id = p_organization_unit_id THEN
        RAISE EXCEPTION 'Organization Unit cannot become its own parent'
            USING ERRCODE = '23514';
    END IF;
    IF proposed_parent_id IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM organization_unit AS parent_unit
        JOIN organization_unit_version AS parent_version
          ON parent_version.tenant_record_id = parent_unit.tenant_record_id
         AND parent_version.organization_unit_id = parent_unit.organization_unit_id
        WHERE parent_unit.tenant_record_id = p_tenant_record_id
          AND parent_unit.organization_unit_id = proposed_parent_id
          AND parent_unit.recorded_from <= pg_catalog.transaction_timestamp()
          AND (parent_unit.recorded_to IS NULL OR pg_catalog.transaction_timestamp() < parent_unit.recorded_to)
          AND parent_version.recorded_from <= pg_catalog.transaction_timestamp()
          AND (parent_version.recorded_to IS NULL OR pg_catalog.transaction_timestamp() < parent_version.recorded_to)
          AND parent_version.effective_from <= effective_on
          AND (parent_version.effective_to IS NULL OR effective_on < parent_version.effective_to)
    ) THEN
        RAISE EXCEPTION 'proposed parent is not visible in the same tenant at the requested coordinate'
            USING ERRCODE = '23503';
    END IF;

    expected_unit_digest := organization_unit_review_snapshot_digest(
        p_tenant_record_id,
        p_organization_unit_id,
        effective_on,
        pg_catalog.transaction_timestamp()
    );
    expected_hierarchy_digest := organization_hierarchy_review_snapshot_digest(
        p_tenant_record_id,
        effective_on,
        pg_catalog.transaction_timestamp()
    );
    IF expected_unit_digest IS DISTINCT FROM review_payload ->> 'organization_unit_snapshot_digest'
       OR expected_hierarchy_digest IS DISTINCT FROM review_payload ->> 'hierarchy_snapshot_digest' THEN
        RAISE EXCEPTION 'reviewed Organization hierarchy snapshots are stale at authoritative application time'
            USING ERRCODE = '40001';
    END IF;

    IF proposed_parent_id IS NOT NULL THEN
        WITH RECURSIVE effective_boundaries(effective_coordinate) AS (
            SELECT effective_on
            UNION
            SELECT version.effective_from
            FROM organization_unit_version AS version
            WHERE version.tenant_record_id = p_tenant_record_id
              AND version.recorded_from <= pg_catalog.transaction_timestamp()
              AND (version.recorded_to IS NULL OR pg_catalog.transaction_timestamp() < version.recorded_to)
              AND version.effective_from > effective_on
              AND (
                    predecessor.effective_to IS NULL
                    OR version.effective_from < predecessor.effective_to
              )
            UNION
            SELECT version.effective_to
            FROM organization_unit_version AS version
            WHERE version.tenant_record_id = p_tenant_record_id
              AND version.recorded_from <= pg_catalog.transaction_timestamp()
              AND (version.recorded_to IS NULL OR pg_catalog.transaction_timestamp() < version.recorded_to)
              AND version.effective_to IS NOT NULL
              AND version.effective_to > effective_on
              AND (
                    predecessor.effective_to IS NULL
                    OR version.effective_to < predecessor.effective_to
              )
        ), parent_path(
            effective_coordinate,
            organization_unit_id,
            parent_organization_unit_id
        ) AS (
            SELECT
                boundary.effective_coordinate,
                version.organization_unit_id,
                version.parent_organization_unit_id
            FROM effective_boundaries AS boundary
            JOIN organization_unit_version AS version
              ON version.tenant_record_id = p_tenant_record_id
             AND version.organization_unit_id = proposed_parent_id
             AND version.recorded_from <= pg_catalog.transaction_timestamp()
             AND (version.recorded_to IS NULL OR pg_catalog.transaction_timestamp() < version.recorded_to)
             AND version.effective_from <= boundary.effective_coordinate
             AND (
                    version.effective_to IS NULL
                    OR boundary.effective_coordinate < version.effective_to
             )
            UNION
            SELECT
                path.effective_coordinate,
                version.organization_unit_id,
                version.parent_organization_unit_id
            FROM parent_path AS path
            JOIN organization_unit_version AS version
              ON version.tenant_record_id = p_tenant_record_id
             AND version.organization_unit_id = path.parent_organization_unit_id
             AND version.recorded_from <= pg_catalog.transaction_timestamp()
             AND (version.recorded_to IS NULL OR pg_catalog.transaction_timestamp() < version.recorded_to)
             AND version.effective_from <= path.effective_coordinate
             AND (
                    version.effective_to IS NULL
                    OR path.effective_coordinate < version.effective_to
             )
            WHERE path.parent_organization_unit_id IS NOT NULL
        )
        SELECT
            EXISTS (
                SELECT 1
                FROM effective_boundaries AS boundary
                WHERE (
                    SELECT count(*)
                    FROM organization_unit_version AS version
                    WHERE version.tenant_record_id = p_tenant_record_id
                      AND version.organization_unit_id = proposed_parent_id
                      AND version.recorded_from <= pg_catalog.transaction_timestamp()
                      AND (
                            version.recorded_to IS NULL
                            OR pg_catalog.transaction_timestamp() < version.recorded_to
                      )
                      AND version.effective_from <= boundary.effective_coordinate
                      AND (
                            version.effective_to IS NULL
                            OR boundary.effective_coordinate < version.effective_to
                      )
                ) <> 1
            ),
            EXISTS (
                SELECT 1
                FROM parent_path
                WHERE organization_unit_id = p_organization_unit_id
                   OR parent_organization_unit_id = p_organization_unit_id
            )
        INTO parent_gap_found, cycle_found;

        IF parent_gap_found THEN
            RAISE EXCEPTION 'proposed parent is not visible throughout successor effective interval'
                USING ERRCODE = '23503';
        END IF;

        IF cycle_found THEN
            RAISE EXCEPTION 'organization hierarchy change would create a parent cycle'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    event_json := pg_catalog.jsonb_build_object(
        'data', pg_catalog.jsonb_build_object(
            'high_impact', true,
            'result_code', 'organization_hierarchy_changed'
        ),
        'datacontenttype', 'application/json',
        'id', p_audit_event_record_id::text,
        'orgmetraactor', p_applied_by_actor_reference,
        'orgmetraconfirmation', 'human_confirmation:' || review_reference::text,
        'orgmetraevidence', p_review_digest,
        'orgmetrapurpose', 'organization_hierarchy_change_apply',
        'orgmetrareason', reason,
        'orgmetratenant', p_tenant_record_id::text,
        'source', 'urn:orgmetra:organization_core',
        'specversion', '1.0',
        'subject', 'organization_unit:' || p_organization_unit_id::text,
        'time', to_char(
            pg_catalog.transaction_timestamp() AT TIME ZONE 'UTC',
            'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'
        ),
        'type', 'orgmetra.organization.hierarchy_changed'
    )::text;
    event_digest := encode(
        public.digest(pg_catalog.convert_to(event_json, 'UTF8'), 'sha256'),
        'hex'
    );
    PERFORM public.record_audit_outbox_event(
        p_tenant_record_id,
        p_audit_event_record_id,
        p_outbox_delivery_record_id,
        event_json,
        event_digest,
        'orgmetra_domain_events'
    );

    INSERT INTO organization_hierarchy_change_application_record (
        tenant_record_id,
        organization_hierarchy_change_application_record_id,
        organization_unit_id,
        predecessor_organization_unit_version_id,
        successor_organization_unit_version_id,
        organization_hierarchy_change_reference,
        current_parent_organization_unit_id,
        proposed_parent_organization_unit_id,
        canonical_review_json,
        review_evidence_digest_sha256,
        organization_unit_snapshot_digest_sha256,
        hierarchy_snapshot_digest_sha256,
        requester_actor_reference,
        reviewer_actor_reference,
        applied_by_actor_reference,
        reason_code,
        effective_on,
        review_packet_recorded_at,
        audit_event_record_id,
        outbox_delivery_record_id
    ) VALUES (
        p_tenant_record_id,
        p_application_record_id,
        p_organization_unit_id,
        predecessor.organization_unit_version_id,
        p_successor_version_id,
        review_reference,
        current_parent_id,
        proposed_parent_id,
        p_canonical_review_json,
        p_review_digest,
        review_payload ->> 'organization_unit_snapshot_digest',
        review_payload ->> 'hierarchy_snapshot_digest',
        requester,
        reviewer,
        p_applied_by_actor_reference,
        reason,
        effective_on,
        review_recorded_at,
        p_audit_event_record_id,
        p_outbox_delivery_record_id
    );

    UPDATE organization_unit_version
    SET recorded_to = pg_catalog.transaction_timestamp()
    WHERE tenant_record_id = p_tenant_record_id
      AND organization_unit_version_id = predecessor.organization_unit_version_id;

    IF predecessor.effective_from < effective_on THEN
        preserved_version_id := pg_catalog.gen_random_uuid();
        INSERT INTO organization_unit_version (
            tenant_record_id,
            organization_unit_version_id,
            organization_unit_id,
            unit_name,
            organization_type_code,
            parent_organization_unit_id,
            effective_from,
            effective_to,
            recorded_from,
            organization_hierarchy_change_application_record_id
        ) VALUES (
            p_tenant_record_id,
            preserved_version_id,
            p_organization_unit_id,
            predecessor.unit_name,
            predecessor.organization_type_code,
            predecessor.parent_organization_unit_id,
            predecessor.effective_from,
            effective_on,
            pg_catalog.transaction_timestamp(),
            p_application_record_id
        );
    END IF;

    INSERT INTO organization_unit_version (
        tenant_record_id,
        organization_unit_version_id,
        organization_unit_id,
        unit_name,
        organization_type_code,
        parent_organization_unit_id,
        effective_from,
        effective_to,
        recorded_from,
        organization_hierarchy_change_application_record_id
    ) VALUES (
        p_tenant_record_id,
        p_successor_version_id,
        p_organization_unit_id,
        predecessor.unit_name,
        predecessor.organization_type_code,
        proposed_parent_id,
        effective_on,
        predecessor.effective_to,
        pg_catalog.transaction_timestamp(),
        p_application_record_id
    );
END;
$$;

COMMENT ON FUNCTION apply_organization_hierarchy_change(uuid, uuid, uuid, uuid, uuid, text, text, text, uuid, uuid) IS
    'Serializes one tenant hierarchy graph, validates an exact v1 non-authorizing review against fresh same-tenant bitemporal truth, requires one visible proposed-parent version throughout the successor interval, rejects stale evidence and cycles, emits organization_core-owned immutable human-confirmed audit/outbox evidence, and records preserved/successor business-time truth.';

REVOKE ALL ON FUNCTION apply_organization_hierarchy_change(
    uuid, uuid, uuid, uuid, uuid, text, text, text, uuid, uuid
) FROM PUBLIC;
