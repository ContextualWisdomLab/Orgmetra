-- Apply one reviewed Organization Unit parent change to authoritative bitemporal
-- HRIS truth. The relation stores value-minimized governance evidence only; it
-- does not copy Person, worker, compensation, rating, or free-form HR values.

ALTER TABLE organization_unit_version
    ADD CONSTRAINT organization_unit_version_tenant_unit_version_unique
    UNIQUE (tenant_record_id, organization_unit_id, organization_unit_version_id);

CREATE TABLE organization_hierarchy_change_application_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    organization_hierarchy_change_application_record_id uuid PRIMARY KEY,
    organization_unit_id uuid NOT NULL,
    predecessor_organization_unit_version_id uuid NOT NULL,
    successor_organization_unit_version_id uuid NOT NULL,
    organization_hierarchy_change_reference uuid NOT NULL,
    current_parent_organization_unit_id uuid,
    proposed_parent_organization_unit_id uuid,
    canonical_review_json text NOT NULL,
    review_evidence_digest_sha256 text NOT NULL,
    organization_unit_snapshot_digest_sha256 text NOT NULL,
    hierarchy_snapshot_digest_sha256 text NOT NULL,
    requester_actor_reference text NOT NULL,
    reviewer_actor_reference text NOT NULL,
    applied_by_actor_reference text NOT NULL,
    reason_code text NOT NULL,
    effective_on date NOT NULL,
    review_packet_recorded_at timestamptz NOT NULL,
    audit_event_record_id uuid NOT NULL,
    outbox_delivery_record_id uuid NOT NULL,
    application_state text NOT NULL DEFAULT 'applied_after_human_confirmation',
    decision_authority_state text NOT NULL DEFAULT 'human_review_then_authoritative_application',
    recorded_at timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    CONSTRAINT organization_hierarchy_application_id_operational_check
        CHECK (public.is_operational_uuid(organization_hierarchy_change_application_record_id)),
    CONSTRAINT organization_hierarchy_successor_id_operational_check
        CHECK (public.is_operational_uuid(successor_organization_unit_version_id)),
    CONSTRAINT organization_hierarchy_change_reference_v4_check
        CHECK (
            organization_hierarchy_change_reference::text ~
            '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT organization_hierarchy_application_unit_tenant_fk
        FOREIGN KEY (tenant_record_id, organization_unit_id)
        REFERENCES organization_unit(tenant_record_id, organization_unit_id),
    CONSTRAINT organization_hierarchy_application_predecessor_fk
        FOREIGN KEY (
            tenant_record_id,
            organization_unit_id,
            predecessor_organization_unit_version_id
        )
        REFERENCES organization_unit_version(
            tenant_record_id,
            organization_unit_id,
            organization_unit_version_id
        ),
    CONSTRAINT organization_hierarchy_application_successor_fk
        FOREIGN KEY (
            tenant_record_id,
            organization_unit_id,
            successor_organization_unit_version_id
        )
        REFERENCES organization_unit_version(
            tenant_record_id,
            organization_unit_id,
            organization_unit_version_id
        ) DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT organization_hierarchy_application_current_parent_tenant_fk
        FOREIGN KEY (tenant_record_id, current_parent_organization_unit_id)
        REFERENCES organization_unit(tenant_record_id, organization_unit_id),
    CONSTRAINT organization_hierarchy_application_proposed_parent_tenant_fk
        FOREIGN KEY (tenant_record_id, proposed_parent_organization_unit_id)
        REFERENCES organization_unit(tenant_record_id, organization_unit_id),
    CONSTRAINT organization_hierarchy_application_audit_tenant_fk
        FOREIGN KEY (tenant_record_id, audit_event_record_id)
        REFERENCES audit_event_record(tenant_record_id, audit_event_record_id),
    CONSTRAINT organization_hierarchy_application_outbox_tenant_fk
        FOREIGN KEY (tenant_record_id, outbox_delivery_record_id)
        REFERENCES outbox_delivery_record(tenant_record_id, outbox_delivery_record_id),
    CONSTRAINT organization_hierarchy_application_parent_change_check
        CHECK (current_parent_organization_unit_id IS DISTINCT FROM proposed_parent_organization_unit_id),
    CONSTRAINT organization_hierarchy_application_not_self_parent_check
        CHECK (
            proposed_parent_organization_unit_id IS NULL
            OR proposed_parent_organization_unit_id <> organization_unit_id
        ),
    CONSTRAINT organization_hierarchy_application_review_digest_check
        CHECK (review_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT organization_hierarchy_application_unit_digest_check
        CHECK (organization_unit_snapshot_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT organization_hierarchy_application_graph_digest_check
        CHECK (hierarchy_snapshot_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT organization_hierarchy_application_requester_actor_check
        CHECK (
            requester_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT organization_hierarchy_application_reviewer_actor_check
        CHECK (
            reviewer_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT organization_hierarchy_application_applier_actor_check
        CHECK (
            applied_by_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT organization_hierarchy_application_actor_separation_check
        CHECK (
            requester_actor_reference <> reviewer_actor_reference
            AND reviewer_actor_reference <> applied_by_actor_reference
        ),
    CONSTRAINT organization_hierarchy_application_reason_check
        CHECK (
            reason_code IN (
                'administrative_correction',
                'legal_entity_restructure',
                'operating_model_change',
                'organizational_realignment'
            )
        ),
    CONSTRAINT organization_hierarchy_application_chronology_check
        CHECK (review_packet_recorded_at <= recorded_at),
    CONSTRAINT organization_hierarchy_application_state_check
        CHECK (application_state = 'applied_after_human_confirmation'),
    CONSTRAINT organization_hierarchy_application_authority_check
        CHECK (decision_authority_state = 'human_review_then_authoritative_application'),
    CONSTRAINT organization_hierarchy_application_tenant_identity_unique
        UNIQUE (tenant_record_id, organization_hierarchy_change_application_record_id),
    CONSTRAINT organization_hierarchy_application_review_reference_unique
        UNIQUE (tenant_record_id, organization_hierarchy_change_reference),
    CONSTRAINT organization_hierarchy_application_successor_unique
        UNIQUE (tenant_record_id, successor_organization_unit_version_id),
    CONSTRAINT organization_hierarchy_application_audit_unique
        UNIQUE (tenant_record_id, audit_event_record_id),
    CONSTRAINT organization_hierarchy_application_outbox_unique
        UNIQUE (tenant_record_id, outbox_delivery_record_id)
);

COMMENT ON TABLE organization_hierarchy_change_application_record IS
    'Immutable evidence linking one reviewed Organization Unit parent proposal to one authoritative bitemporal successor plus atomic audit/outbox evidence.';

ALTER TABLE organization_unit_version
    ADD COLUMN organization_hierarchy_change_application_record_id uuid;

ALTER TABLE organization_unit_version
    ADD CONSTRAINT organization_unit_version_hierarchy_application_tenant_fk
    FOREIGN KEY (tenant_record_id, organization_hierarchy_change_application_record_id)
    REFERENCES organization_hierarchy_change_application_record(
        tenant_record_id,
        organization_hierarchy_change_application_record_id
    );

CREATE FUNCTION organization_unit_review_snapshot_digest(
    checked_tenant_record_id uuid,
    checked_organization_unit_id uuid,
    checked_effective_on date,
    checked_known_at timestamptz
)
RETURNS text
LANGUAGE sql
STABLE
STRICT
SET search_path = pg_catalog, public, pg_temp
AS $$
    WITH visible AS (
        SELECT pg_catalog.jsonb_build_object(
            'effective_from', version.effective_from,
            'effective_to', version.effective_to,
            'organization_type_code', version.organization_type_code,
            'organization_unit_id', version.organization_unit_id,
            'organization_unit_version_id', version.organization_unit_version_id,
            'parent_organization_unit_id', version.parent_organization_unit_id,
            'unit_name', version.unit_name
        )::text AS canonical_snapshot
        FROM organization_unit AS unit
        JOIN organization_unit_version AS version
          ON version.tenant_record_id = unit.tenant_record_id
         AND version.organization_unit_id = unit.organization_unit_id
        WHERE unit.tenant_record_id = checked_tenant_record_id
          AND unit.organization_unit_id = checked_organization_unit_id
          AND unit.recorded_from <= checked_known_at
          AND (unit.recorded_to IS NULL OR checked_known_at < unit.recorded_to)
          AND version.recorded_from <= checked_known_at
          AND (version.recorded_to IS NULL OR checked_known_at < version.recorded_to)
          AND version.effective_from <= checked_effective_on
          AND (version.effective_to IS NULL OR checked_effective_on < version.effective_to)
    )
    SELECT CASE
        WHEN count(*) = 1 THEN encode(
            public.digest(
                pg_catalog.convert_to(min(canonical_snapshot), 'UTF8'),
                'sha256'
            ),
            'hex'
        )
        ELSE NULL
    END
    FROM visible;
$$;

COMMENT ON FUNCTION organization_unit_review_snapshot_digest(uuid, uuid, date, timestamptz) IS
    'Returns SHA-256 over exactly one same-tenant visible OrganizationUnitVersion snapshot at one business/system coordinate; missing or ambiguous truth returns NULL.';

CREATE FUNCTION organization_hierarchy_review_snapshot_digest(
    checked_tenant_record_id uuid,
    checked_effective_on date,
    checked_known_at timestamptz
)
RETURNS text
LANGUAGE sql
STABLE
STRICT
SET search_path = pg_catalog, public, pg_temp
AS $$
    WITH visible AS (
        SELECT
            version.organization_unit_id,
            pg_catalog.jsonb_build_object(
                'organization_unit_id', version.organization_unit_id,
                'organization_unit_version_id', version.organization_unit_version_id,
                'parent_organization_unit_id', version.parent_organization_unit_id
            ) AS snapshot_row
        FROM organization_unit AS unit
        JOIN organization_unit_version AS version
          ON version.tenant_record_id = unit.tenant_record_id
         AND version.organization_unit_id = unit.organization_unit_id
        WHERE unit.tenant_record_id = checked_tenant_record_id
          AND unit.recorded_from <= checked_known_at
          AND (unit.recorded_to IS NULL OR checked_known_at < unit.recorded_to)
          AND version.recorded_from <= checked_known_at
          AND (version.recorded_to IS NULL OR checked_known_at < version.recorded_to)
          AND version.effective_from <= checked_effective_on
          AND (version.effective_to IS NULL OR checked_effective_on < version.effective_to)
    ), aggregate_snapshot AS (
        SELECT pg_catalog.jsonb_agg(snapshot_row ORDER BY organization_unit_id)::text AS canonical_snapshot
        FROM visible
    )
    SELECT CASE
        WHEN canonical_snapshot IS NULL THEN NULL
        ELSE encode(
            public.digest(pg_catalog.convert_to(canonical_snapshot, 'UTF8'), 'sha256'),
            'hex'
        )
    END
    FROM aggregate_snapshot;
$$;

COMMENT ON FUNCTION organization_hierarchy_review_snapshot_digest(uuid, date, timestamptz) IS
    'Returns SHA-256 over the deterministic set of same-tenant visible Organization Unit parent facts at one business/system coordinate.';

CREATE FUNCTION validate_organization_hierarchy_change_review_evidence(
    p_canonical_review_json text,
    p_review_digest text,
    p_tenant_record_id uuid,
    p_organization_unit_id uuid,
    p_effective_on date
)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    review_json json;
    review_payload jsonb;
    review_keys text[];
    key_count integer;
    review_recorded_at timestamptz;
    unit_reference text;
    expected_keys constant text[] := ARRAY[
        'contains_employment_decision',
        'contains_person_identifier',
        'contains_worker_value',
        'current_parent_organization_unit_reference',
        'decision_authority',
        'effective_on',
        'evidence_version',
        'hierarchy_snapshot_digest',
        'human_review_required',
        'mutation_state',
        'next_action',
        'organization_hierarchy_change_reference',
        'organization_unit_reference',
        'organization_unit_snapshot_digest',
        'proposed_parent_organization_unit_reference',
        'purpose_code',
        'reason_code',
        'recorded_at',
        'requester_reference',
        'review_state',
        'reviewer_reference',
        'scope_verification_state',
        'tenant_record_id'
    ];
    expected_next_action constant text :=
        'Within tenant_record_id, re-resolve the Organization Unit, current parent, proposed parent, '
        'and current hierarchy through authoritative Orgmetra HRIS boundaries at effective_on and the '
        'current system-recorded cutoff; prove every referenced Organization Unit is same-tenant and '
        'valid, verify the reviewed unit and hierarchy snapshot digests plus reason, prove requester/'
        'reviewer authoritative actor separation, reject self-parenting, cycles, multiple visible parents, '
        'or stale current-parent evidence, then invoke the authoritative organization-hierarchy mutation '
        'boundary with immutable audit/outbox evidence. This packet is review evidence only and is not '
        'authorization to mutate HRIS truth or make an employment decision.';
BEGIN
    IF p_canonical_review_json IS NULL
       OR p_review_digest IS NULL
       OR p_tenant_record_id IS NULL
       OR p_organization_unit_id IS NULL
       OR p_effective_on IS NULL THEN
        RETURN false;
    END IF;

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

    IF pg_catalog.jsonb_typeof(review_payload) IS DISTINCT FROM 'object' THEN
        RETURN false;
    END IF;

    SELECT count(*), array_agg(key ORDER BY key COLLATE "C")
    INTO key_count, review_keys
    FROM pg_catalog.json_object_keys(review_json) AS key_set(key);
    IF key_count <> 23 OR review_keys <> expected_keys THEN
        RETURN false;
    END IF;

    unit_reference := 'organization_unit:' || p_organization_unit_id::text;
    IF pg_catalog.jsonb_typeof(review_payload -> 'tenant_record_id') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'organization_unit_reference') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'effective_on') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'purpose_code') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'evidence_version') IS DISTINCT FROM 'number'
       OR pg_catalog.jsonb_typeof(review_payload -> 'review_state') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'scope_verification_state') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'mutation_state') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'decision_authority') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'next_action') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'human_review_required') IS DISTINCT FROM 'boolean'
       OR pg_catalog.jsonb_typeof(review_payload -> 'contains_person_identifier') IS DISTINCT FROM 'boolean'
       OR pg_catalog.jsonb_typeof(review_payload -> 'contains_worker_value') IS DISTINCT FROM 'boolean'
       OR pg_catalog.jsonb_typeof(review_payload -> 'contains_employment_decision') IS DISTINCT FROM 'boolean'
       OR pg_catalog.jsonb_typeof(review_payload -> 'organization_unit_snapshot_digest') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'hierarchy_snapshot_digest') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'organization_hierarchy_change_reference') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'requester_reference') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'reviewer_reference') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'reason_code') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(review_payload -> 'recorded_at') IS DISTINCT FROM 'string'
       OR (
            pg_catalog.jsonb_typeof(review_payload -> 'current_parent_organization_unit_reference')
                IS DISTINCT FROM 'string'
            AND pg_catalog.jsonb_typeof(review_payload -> 'current_parent_organization_unit_reference')
                IS DISTINCT FROM 'null'
       )
       OR (
            pg_catalog.jsonb_typeof(review_payload -> 'proposed_parent_organization_unit_reference')
                IS DISTINCT FROM 'string'
            AND pg_catalog.jsonb_typeof(review_payload -> 'proposed_parent_organization_unit_reference')
                IS DISTINCT FROM 'null'
       )
       OR (
            pg_catalog.jsonb_typeof(review_payload -> 'current_parent_organization_unit_reference') = 'string'
            AND review_payload ->> 'current_parent_organization_unit_reference'
                !~ '^organization_unit:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
       )
       OR (
            pg_catalog.jsonb_typeof(review_payload -> 'proposed_parent_organization_unit_reference') = 'string'
            AND review_payload ->> 'proposed_parent_organization_unit_reference'
                !~ '^organization_unit:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
       )
       OR review_payload ->> 'tenant_record_id' IS DISTINCT FROM p_tenant_record_id::text
       OR review_payload ->> 'organization_unit_reference' IS DISTINCT FROM unit_reference
       OR review_payload ->> 'effective_on' IS DISTINCT FROM p_effective_on::text
       OR review_payload ->> 'purpose_code' IS DISTINCT FROM 'organization_hierarchy_change_review'
       OR review_payload ->> 'evidence_version' IS DISTINCT FROM '1'
       OR review_payload ->> 'review_state' IS DISTINCT FROM 'requires_human_review'
       OR review_payload ->> 'scope_verification_state' IS DISTINCT FROM 'requires_authoritative_resolution'
       OR review_payload ->> 'mutation_state' IS DISTINCT FROM 'not_authorized_to_apply'
       OR review_payload ->> 'decision_authority' IS DISTINCT FROM 'human_review_only'
       OR review_payload ->> 'next_action' IS DISTINCT FROM expected_next_action
       OR review_payload ->> 'human_review_required' IS DISTINCT FROM 'true'
       OR review_payload ->> 'contains_person_identifier' IS DISTINCT FROM 'false'
       OR review_payload ->> 'contains_worker_value' IS DISTINCT FROM 'false'
       OR review_payload ->> 'contains_employment_decision' IS DISTINCT FROM 'false'
       OR review_payload ->> 'organization_unit_snapshot_digest' IS NULL
       OR review_payload ->> 'organization_unit_snapshot_digest' !~ '^[0-9a-f]{64}$'
       OR review_payload ->> 'hierarchy_snapshot_digest' IS NULL
       OR review_payload ->> 'hierarchy_snapshot_digest' !~ '^[0-9a-f]{64}$'
       OR review_payload ->> 'organization_hierarchy_change_reference'
          IS NULL
       OR review_payload ->> 'organization_hierarchy_change_reference'
          !~ '^organization_hierarchy_change:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
       OR review_payload ->> 'requester_reference'
          IS NULL
       OR review_payload ->> 'requester_reference'
          !~ '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
       OR review_payload ->> 'reviewer_reference'
          IS NULL
       OR review_payload ->> 'reviewer_reference'
          !~ '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
       OR review_payload ->> 'requester_reference'
          IS NOT DISTINCT FROM review_payload ->> 'reviewer_reference'
       OR review_payload ->> 'reason_code' IS NULL
       OR review_payload ->> 'reason_code' NOT IN (
            'administrative_correction',
            'legal_entity_restructure',
            'operating_model_change',
            'organizational_realignment'
       ) THEN
        RETURN false;
    END IF;

    BEGIN
        review_recorded_at := (review_payload ->> 'recorded_at')::timestamptz;
    EXCEPTION WHEN others THEN
        RETURN false;
    END;
    IF review_recorded_at IS NULL
       OR review_recorded_at > pg_catalog.transaction_timestamp() THEN
        RETURN false;
    END IF;

    RETURN true;
END;
$$;

COMMENT ON FUNCTION validate_organization_hierarchy_change_review_evidence(text, text, uuid, uuid, date) IS
    'Validates the exact v1 value-minimized Organization hierarchy review shape, digest, tenant/unit/effective scope, fixed non-authorizing states, actor separation and issuance chronology.';

CREATE FUNCTION protect_organization_hierarchy_application_history()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'organization hierarchy application evidence is append-only'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER organization_hierarchy_application_append_only_guard
BEFORE UPDATE OR DELETE ON organization_hierarchy_change_application_record
FOR EACH ROW
EXECUTE FUNCTION protect_organization_hierarchy_application_history();

CREATE FUNCTION reject_organization_hierarchy_application_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'organization hierarchy application evidence cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER organization_hierarchy_application_truncate_guard
BEFORE TRUNCATE ON organization_hierarchy_change_application_record
FOR EACH STATEMENT
EXECUTE FUNCTION reject_organization_hierarchy_application_truncate();

REVOKE TRUNCATE ON organization_hierarchy_change_application_record FROM PUBLIC;

CREATE FUNCTION validate_organization_hierarchy_application_audit()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    audit_payload jsonb;
    review_payload jsonb;
    review_recorded_at timestamptz;
    outbox_audit_id uuid;
BEGIN
    IF NEW.recorded_at IS DISTINCT FROM pg_catalog.transaction_timestamp() THEN
        RAISE EXCEPTION 'organization hierarchy application recorded_at must equal transaction timestamp'
            USING ERRCODE = '22023';
    END IF;

    IF NOT validate_organization_hierarchy_change_review_evidence(
        NEW.canonical_review_json,
        NEW.review_evidence_digest_sha256,
        NEW.tenant_record_id,
        NEW.organization_unit_id,
        NEW.effective_on
    ) THEN
        RAISE EXCEPTION 'organization hierarchy review evidence is invalid or out of scope'
            USING ERRCODE = '23514';
    END IF;

    review_payload := NEW.canonical_review_json::jsonb;
    review_recorded_at := (review_payload ->> 'recorded_at')::timestamptz;
    IF review_payload ->> 'organization_hierarchy_change_reference'
           IS DISTINCT FROM 'organization_hierarchy_change:' || NEW.organization_hierarchy_change_reference::text
       OR review_payload ->> 'current_parent_organization_unit_reference'
           IS DISTINCT FROM (
               CASE
                WHEN NEW.current_parent_organization_unit_id IS NULL THEN NULL
                ELSE 'organization_unit:' || NEW.current_parent_organization_unit_id::text
               END
           )
       OR review_payload ->> 'proposed_parent_organization_unit_reference'
           IS DISTINCT FROM (
               CASE
                WHEN NEW.proposed_parent_organization_unit_id IS NULL THEN NULL
                ELSE 'organization_unit:' || NEW.proposed_parent_organization_unit_id::text
               END
           )
       OR review_payload ->> 'organization_unit_snapshot_digest'
           IS DISTINCT FROM NEW.organization_unit_snapshot_digest_sha256
       OR review_payload ->> 'hierarchy_snapshot_digest'
           IS DISTINCT FROM NEW.hierarchy_snapshot_digest_sha256
       OR review_payload ->> 'requester_reference'
           IS DISTINCT FROM NEW.requester_actor_reference
       OR review_payload ->> 'reviewer_reference'
           IS DISTINCT FROM NEW.reviewer_actor_reference
       OR review_payload ->> 'reason_code' IS DISTINCT FROM NEW.reason_code
       OR review_recorded_at IS DISTINCT FROM NEW.review_packet_recorded_at THEN
        RAISE EXCEPTION 'organization hierarchy application columns do not match the reviewed evidence'
            USING ERRCODE = '23514';
    END IF;

    SELECT canonical_event_json::jsonb
    INTO audit_payload
    FROM audit_event_record
    WHERE tenant_record_id = NEW.tenant_record_id
      AND audit_event_record_id = NEW.audit_event_record_id;

    IF audit_payload IS NULL
       OR audit_payload ->> 'subject' <> 'organization_unit:' || NEW.organization_unit_id::text
       OR audit_payload ->> 'orgmetraactor' <> NEW.applied_by_actor_reference
       OR audit_payload ->> 'orgmetrapurpose' <> 'organization_hierarchy_change_apply'
       OR audit_payload ->> 'orgmetrareason' <> NEW.reason_code
       OR audit_payload ->> 'orgmetraevidence' <> NEW.review_evidence_digest_sha256
       OR audit_payload #>> '{data,result_code}' <> 'organization_hierarchy_changed'
       OR audit_payload #>> '{data,high_impact}' <> 'true'
       OR audit_payload ->> 'orgmetraconfirmation'
          <> 'human_confirmation:' || NEW.organization_hierarchy_change_reference::text THEN
        RAISE EXCEPTION 'organization hierarchy audit event does not match the applied review'
            USING ERRCODE = '23514';
    END IF;

    SELECT audit_event_record_id
    INTO outbox_audit_id
    FROM outbox_delivery_record
    WHERE tenant_record_id = NEW.tenant_record_id
      AND outbox_delivery_record_id = NEW.outbox_delivery_record_id;
    IF outbox_audit_id IS DISTINCT FROM NEW.audit_event_record_id THEN
        RAISE EXCEPTION 'organization hierarchy outbox does not reference the application audit event'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER organization_hierarchy_application_integrity_guard
BEFORE INSERT ON organization_hierarchy_change_application_record
FOR EACH ROW
EXECUTE FUNCTION validate_organization_hierarchy_application_audit();

CREATE FUNCTION validate_organization_hierarchy_application_successor()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM organization_unit_version AS version
        WHERE version.tenant_record_id = NEW.tenant_record_id
          AND version.organization_unit_id = NEW.organization_unit_id
          AND version.organization_unit_version_id = NEW.successor_organization_unit_version_id
          AND version.organization_hierarchy_change_application_record_id =
              NEW.organization_hierarchy_change_application_record_id
    ) THEN
        RAISE EXCEPTION 'organization hierarchy successor version is not bound to its application'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER organization_hierarchy_application_successor_guard
AFTER INSERT ON organization_hierarchy_change_application_record
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION validate_organization_hierarchy_application_successor();

CREATE FUNCTION apply_organization_hierarchy_change(
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
        SELECT EXISTS (
            SELECT 1
            FROM parent_path
            WHERE organization_unit_id = p_organization_unit_id
               OR parent_organization_unit_id = p_organization_unit_id
        ) INTO cycle_found;

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
        'source', 'urn:orgmetra:people_api',
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
    'Serializes one tenant hierarchy graph, validates an exact v1 non-authorizing review against fresh same-tenant bitemporal Organization Unit truth and reviewed digests, rejects stale parent evidence and cycles, records immutable human-confirmed audit/outbox evidence, closes the predecessor system interval at PostgreSQL transaction time, and inserts preserved/successor business-time truth.';

REVOKE ALL ON FUNCTION apply_organization_hierarchy_change(
    uuid, uuid, uuid, uuid, uuid, text, text, text, uuid, uuid
) FROM PUBLIC;

ALTER TABLE organization_hierarchy_change_application_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_hierarchy_change_application_record FORCE ROW LEVEL SECURITY;
CREATE POLICY organization_hierarchy_change_application_scope_policy
ON organization_hierarchy_change_application_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());
