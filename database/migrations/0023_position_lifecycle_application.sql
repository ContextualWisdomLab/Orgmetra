-- Apply one independently reviewed Position lifecycle transition to authoritative
-- bitemporal Position truth.  Review evidence remains value-minimized; Person,
-- candidate, compensation, assessment, rating, and free-form HR values are not
-- copied into this relation.

BEGIN;

SET LOCAL search_path = public, pg_catalog;

ALTER TABLE public.position_record_version
    ADD CONSTRAINT position_version_lifecycle_scope_unique
    UNIQUE (tenant_record_id, position_record_id, position_record_version_id);

CREATE TABLE position_lifecycle_application_record (
    tenant_record_id uuid NOT NULL REFERENCES public.tenant_record(tenant_record_id),
    position_lifecycle_application_record_id uuid PRIMARY KEY,
    position_record_id uuid NOT NULL,
    predecessor_position_record_version_id uuid NOT NULL,
    successor_position_record_version_id uuid NOT NULL,
    position_lifecycle_change_reference uuid NOT NULL,
    canonical_review_json text NOT NULL,
    review_evidence_digest_sha256 text NOT NULL,
    requester_actor_reference text NOT NULL,
    reviewer_actor_reference text NOT NULL,
    applied_by_actor_reference text NOT NULL,
    current_status_code text NOT NULL,
    proposed_status_code text NOT NULL,
    reason_code text NOT NULL,
    effective_on date NOT NULL,
    reviewed_at timestamptz NOT NULL,
    review_packet_recorded_at timestamptz NOT NULL,
    audit_event_record_id uuid NOT NULL,
    outbox_delivery_record_id uuid NOT NULL,
    application_state text NOT NULL DEFAULT 'applied_after_human_review',
    decision_authority_state text NOT NULL DEFAULT 'human_review_then_authoritative_application',
    recorded_at timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    CONSTRAINT position_lifecycle_application_id_operational_check
        CHECK (public.is_operational_uuid(position_lifecycle_application_record_id)),
    CONSTRAINT position_lifecycle_successor_id_operational_check
        CHECK (public.is_operational_uuid(successor_position_record_version_id)),
    CONSTRAINT position_lifecycle_review_reference_v4_check
        CHECK (
            position_lifecycle_change_reference::text ~
            '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT position_lifecycle_position_tenant_fk
        FOREIGN KEY (tenant_record_id, position_record_id)
        REFERENCES public.position_record(tenant_record_id, position_record_id),
    CONSTRAINT position_lifecycle_predecessor_scope_fk
        FOREIGN KEY (tenant_record_id, position_record_id, predecessor_position_record_version_id)
        REFERENCES public.position_record_version(
            tenant_record_id,
            position_record_id,
            position_record_version_id
        ),
    CONSTRAINT position_lifecycle_successor_scope_fk
        FOREIGN KEY (tenant_record_id, position_record_id, successor_position_record_version_id)
        REFERENCES public.position_record_version(
            tenant_record_id,
            position_record_id,
            position_record_version_id
        ) DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT position_lifecycle_audit_tenant_fk
        FOREIGN KEY (tenant_record_id, audit_event_record_id)
        REFERENCES public.audit_event_record(tenant_record_id, audit_event_record_id),
    CONSTRAINT position_lifecycle_outbox_tenant_fk
        FOREIGN KEY (tenant_record_id, outbox_delivery_record_id)
        REFERENCES public.outbox_delivery_record(tenant_record_id, outbox_delivery_record_id),
    CONSTRAINT position_lifecycle_review_digest_check
        CHECK (review_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT position_lifecycle_requester_actor_check
        CHECK (
            requester_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT position_lifecycle_reviewer_actor_check
        CHECK (
            reviewer_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT position_lifecycle_applier_actor_check
        CHECK (
            applied_by_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT position_lifecycle_actor_separation_check
        CHECK (
            requester_actor_reference <> reviewer_actor_reference
            AND reviewer_actor_reference <> applied_by_actor_reference
        ),
    CONSTRAINT position_lifecycle_current_status_check
        CHECK (current_status_code IN ('active', 'open', 'closed', 'frozen', 'abolished')),
    CONSTRAINT position_lifecycle_proposed_status_check
        CHECK (proposed_status_code IN ('active', 'open', 'closed', 'frozen', 'abolished')),
    CONSTRAINT position_lifecycle_reason_check
        CHECK (reason_code IN ('temporary_freeze', 'position_reactivation', 'position_closure', 'position_abolition')),
    CONSTRAINT position_lifecycle_review_chronology_check
        CHECK (reviewed_at <= review_packet_recorded_at AND review_packet_recorded_at <= recorded_at),
    CONSTRAINT position_lifecycle_application_state_check
        CHECK (application_state = 'applied_after_human_review'),
    CONSTRAINT position_lifecycle_decision_authority_check
        CHECK (decision_authority_state = 'human_review_then_authoritative_application'),
    CONSTRAINT position_lifecycle_application_tenant_identity_unique
        UNIQUE (tenant_record_id, position_lifecycle_application_record_id),
    CONSTRAINT position_lifecycle_review_reference_unique
        UNIQUE (tenant_record_id, position_lifecycle_change_reference),
    CONSTRAINT position_lifecycle_successor_unique
        UNIQUE (tenant_record_id, successor_position_record_version_id),
    CONSTRAINT position_lifecycle_audit_unique
        UNIQUE (tenant_record_id, audit_event_record_id),
    CONSTRAINT position_lifecycle_outbox_unique
        UNIQUE (tenant_record_id, outbox_delivery_record_id)
);

COMMENT ON TABLE position_lifecycle_application_record IS
    'Immutable application evidence linking one reviewed Position lifecycle proposal to one authoritative successor PositionVersion and atomic audit/outbox evidence.';

ALTER TABLE public.position_record_version
    ADD COLUMN position_lifecycle_application_record_id uuid;

ALTER TABLE public.position_record_version
    ADD CONSTRAINT position_version_lifecycle_application_tenant_fk
    FOREIGN KEY (tenant_record_id, position_lifecycle_application_record_id)
    REFERENCES public.position_lifecycle_application_record(
        tenant_record_id,
        position_lifecycle_application_record_id
    );

CREATE FUNCTION public.validate_position_lifecycle_review_evidence(
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
SET search_path = pg_catalog, public, pg_temp
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

    IF (review_payload ->> 'proposed_status_code') IN ('active', 'open')
       AND review_payload ->> 'reason_code' <> 'position_reactivation' THEN
        RETURN false;
    ELSIF review_payload ->> 'proposed_status_code' = 'frozen'
       AND review_payload ->> 'reason_code' <> 'temporary_freeze' THEN
        RETURN false;
    ELSIF review_payload ->> 'proposed_status_code' = 'closed'
       AND review_payload ->> 'reason_code' <> 'position_closure' THEN
        RETURN false;
    ELSIF review_payload ->> 'proposed_status_code' = 'abolished'
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

COMMENT ON FUNCTION public.validate_position_lifecycle_review_evidence(text, text, uuid, uuid, text, text, date) IS
    'Validates exact v1 Position lifecycle review shape, digest, tenant/Position/status/effective scope, human approval state, and chronology without granting mutation authority.';

CREATE FUNCTION public.protect_position_lifecycle_application_history()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'position lifecycle application evidence is append-only'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER position_lifecycle_application_append_only_guard
BEFORE UPDATE OR DELETE ON public.position_lifecycle_application_record
FOR EACH ROW
EXECUTE FUNCTION public.protect_position_lifecycle_application_history();

CREATE FUNCTION public.protect_position_version_history_after_lifecycle_support()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'PositionVersion history cannot be deleted'
            USING ERRCODE = '55000';
    END IF;
    IF OLD.recorded_to IS NOT NULL
       OR NEW.recorded_to IS NULL
       OR NEW.recorded_to IS DISTINCT FROM pg_catalog.transaction_timestamp()
       OR to_jsonb(NEW) - 'recorded_to' <> to_jsonb(OLD) - 'recorded_to' THEN
        RAISE EXCEPTION 'PositionVersion history may only close an open recorded interval at transaction time'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.protect_position_version_history_after_lifecycle_support() IS
    'Prevents delete/in-place rewrite of PositionVersion facts; an open system-recorded interval may only be closed at PostgreSQL transaction time.';

CREATE TRIGGER position_version_lifecycle_history_guard
BEFORE UPDATE OR DELETE ON public.position_record_version
FOR EACH ROW
EXECUTE FUNCTION public.protect_position_version_history_after_lifecycle_support();

CREATE FUNCTION public.validate_position_lifecycle_application_audit()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    audit_payload jsonb;
    review_payload jsonb;
    outbox_audit_id uuid;
BEGIN
    IF NEW.recorded_at IS DISTINCT FROM pg_catalog.transaction_timestamp() THEN
        RAISE EXCEPTION 'position lifecycle application recorded_at must equal transaction timestamp'
            USING ERRCODE = '22023';
    END IF;
    IF NOT validate_position_lifecycle_review_evidence(
        NEW.canonical_review_json,
        NEW.review_evidence_digest_sha256,
        NEW.tenant_record_id,
        NEW.position_record_id,
        NEW.current_status_code,
        NEW.proposed_status_code,
        NEW.effective_on
    ) THEN
        RAISE EXCEPTION 'position lifecycle review evidence is invalid or out of scope'
            USING ERRCODE = '23514';
    END IF;

    review_payload := NEW.canonical_review_json::jsonb;
    IF NEW.position_lifecycle_change_reference IS DISTINCT FROM
           (review_payload ->> 'position_lifecycle_change_reference')::uuid
       OR NEW.requester_actor_reference IS DISTINCT FROM
           review_payload ->> 'requester_actor_reference'
       OR NEW.reviewer_actor_reference IS DISTINCT FROM
           review_payload ->> 'reviewer_actor_reference'
       OR NEW.current_status_code IS DISTINCT FROM
           review_payload ->> 'current_status_code'
       OR NEW.proposed_status_code IS DISTINCT FROM
           review_payload ->> 'proposed_status_code'
       OR NEW.reason_code IS DISTINCT FROM review_payload ->> 'reason_code'
       OR NEW.effective_on IS DISTINCT FROM
           (review_payload ->> 'effective_on')::date
       OR NEW.reviewed_at IS DISTINCT FROM
           (review_payload ->> 'reviewed_at')::timestamptz
       OR NEW.review_packet_recorded_at IS DISTINCT FROM
           (review_payload ->> 'recorded_at')::timestamptz THEN
        RAISE EXCEPTION 'position lifecycle application row does not match reviewed evidence'
            USING ERRCODE = '23514';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM public.position_record_version AS predecessor
        WHERE predecessor.tenant_record_id = NEW.tenant_record_id
          AND predecessor.position_record_id = NEW.position_record_id
          AND predecessor.position_record_version_id = NEW.predecessor_position_record_version_id
          AND predecessor.position_status_code = NEW.current_status_code
          AND predecessor.recorded_from <= pg_catalog.transaction_timestamp()
          AND (predecessor.recorded_to IS NULL
               OR pg_catalog.transaction_timestamp() < predecessor.recorded_to)
          AND predecessor.effective_from <= NEW.effective_on
          AND (predecessor.effective_to IS NULL
               OR NEW.effective_on < predecessor.effective_to)
    ) THEN
        RAISE EXCEPTION 'position lifecycle predecessor is not current at the reviewed effective date'
            USING ERRCODE = '23514';
    END IF;

    audit_payload := (
        SELECT canonical_event_json::jsonb
        FROM public.audit_event_record
        WHERE tenant_record_id = NEW.tenant_record_id
          AND audit_event_record_id = NEW.audit_event_record_id
    );
    IF audit_payload IS NULL
       OR audit_payload ->> 'subject' <> 'position_record:' || NEW.position_record_id::text
       OR audit_payload ->> 'orgmetraactor' <> NEW.applied_by_actor_reference
       OR audit_payload ->> 'orgmetrapurpose' <> 'position_lifecycle_change'
       OR audit_payload ->> 'orgmetrareason' <> NEW.reason_code
       OR audit_payload ->> 'orgmetraevidence' <> NEW.review_evidence_digest_sha256
       OR audit_payload #>> '{data,result_code}' <> 'position_lifecycle_changed'
       OR audit_payload #>> '{data,high_impact}' <> 'true'
       OR audit_payload ->> 'orgmetraconfirmation'
          <> 'human_confirmation:' || NEW.position_lifecycle_change_reference::text THEN
        RAISE EXCEPTION 'position lifecycle audit event does not match the applied review'
            USING ERRCODE = '23514';
    END IF;

    SELECT audit_event_record_id
    INTO outbox_audit_id
    FROM public.outbox_delivery_record
    WHERE tenant_record_id = NEW.tenant_record_id
      AND outbox_delivery_record_id = NEW.outbox_delivery_record_id;
    IF outbox_audit_id IS DISTINCT FROM NEW.audit_event_record_id THEN
        RAISE EXCEPTION 'position lifecycle outbox does not reference the application audit event'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER position_lifecycle_application_integrity_guard
BEFORE INSERT ON public.position_lifecycle_application_record
FOR EACH ROW
EXECUTE FUNCTION public.validate_position_lifecycle_application_audit();

CREATE FUNCTION public.validate_position_lifecycle_application_successor()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    successor public.position_record_version%ROWTYPE;
BEGIN
    SELECT version.*
    INTO successor
    FROM public.position_record_version AS version
    WHERE version.tenant_record_id = NEW.tenant_record_id
      AND version.position_record_id = NEW.position_record_id
      AND version.position_record_version_id = NEW.successor_position_record_version_id;
    IF NOT FOUND
       OR successor.position_status_code <> NEW.proposed_status_code
       OR successor.effective_from <> NEW.effective_on
       OR successor.recorded_from IS DISTINCT FROM pg_catalog.transaction_timestamp()
       OR successor.recorded_to IS NOT NULL
       OR successor.position_lifecycle_application_record_id
          IS DISTINCT FROM NEW.position_lifecycle_application_record_id THEN
        RAISE EXCEPTION 'position lifecycle successor does not match the application evidence'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER position_lifecycle_application_successor_guard
AFTER INSERT ON public.position_lifecycle_application_record
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION public.validate_position_lifecycle_application_successor();

CREATE FUNCTION public.reject_position_lifecycle_history_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'Position lifecycle history cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER position_lifecycle_application_truncate_guard
BEFORE TRUNCATE ON public.position_lifecycle_application_record
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_position_lifecycle_history_truncate();

CREATE TRIGGER position_record_version_lifecycle_truncate_guard
BEFORE TRUNCATE ON public.position_record_version
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_position_lifecycle_history_truncate();

REVOKE TRUNCATE ON public.position_lifecycle_application_record, public.position_record_version FROM PUBLIC;

CREATE FUNCTION public.apply_position_lifecycle_change(
    p_tenant_record_id uuid,
    p_position_record_id uuid,
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
    predecessor public.position_record_version%ROWTYPE;
    preserved_version_id uuid;
    event_json text;
    event_digest text;
    current_status text;
    proposed_status text;
    reason text;
    effective_on date;
    requester text;
    reviewer text;
    reviewed_at timestamptz;
    review_recorded_at timestamptz;
    review_reference uuid;
BEGIN
    IF is_operational_uuid(p_tenant_record_id) IS NOT TRUE
       OR is_operational_uuid(p_position_record_id) IS NOT TRUE
       OR is_operational_uuid(p_expected_predecessor_version_id) IS NOT TRUE
       OR is_operational_uuid(p_successor_version_id) IS NOT TRUE
       OR is_operational_uuid(p_application_record_id) IS NOT TRUE
       OR is_operational_uuid(p_audit_event_record_id) IS NOT TRUE
       OR is_operational_uuid(p_outbox_delivery_record_id) IS NOT TRUE THEN
        RAISE EXCEPTION 'position lifecycle application requires operational UUID identities'
            USING ERRCODE = '23514';
    END IF;
    IF p_applied_by_actor_reference
       !~ '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' THEN
        RAISE EXCEPTION 'position lifecycle applier must be a pseudonymous actor UUIDv4 correlation'
            USING ERRCODE = '23514';
    END IF;

    review_payload := p_canonical_review_json::jsonb;
    current_status := review_payload ->> 'current_status_code';
    proposed_status := review_payload ->> 'proposed_status_code';
    reason := review_payload ->> 'reason_code';
    effective_on := (review_payload ->> 'effective_on')::date;
    requester := review_payload ->> 'requester_actor_reference';
    reviewer := review_payload ->> 'reviewer_actor_reference';
    reviewed_at := (review_payload ->> 'reviewed_at')::timestamptz;
    review_recorded_at := (review_payload ->> 'recorded_at')::timestamptz;
    review_reference := (review_payload ->> 'position_lifecycle_change_reference')::uuid;

    IF reviewer = p_applied_by_actor_reference THEN
        RAISE EXCEPTION 'position lifecycle reviewer and applier must be distinct actors'
            USING ERRCODE = '23514';
    END IF;

    PERFORM 1
    FROM public.position_record
    WHERE tenant_record_id = p_tenant_record_id
      AND position_record_id = p_position_record_id
      AND recorded_from <= pg_catalog.transaction_timestamp()
      AND (recorded_to IS NULL OR pg_catalog.transaction_timestamp() < recorded_to)
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Position is not current in the tenant'
            USING ERRCODE = '23503';
    END IF;

    SELECT version.*
    INTO predecessor
    FROM public.position_record_version AS version
    WHERE version.tenant_record_id = p_tenant_record_id
      AND version.position_record_id = p_position_record_id
      AND version.recorded_from <= pg_catalog.transaction_timestamp()
      AND (version.recorded_to IS NULL OR pg_catalog.transaction_timestamp() < version.recorded_to)
      AND version.effective_from <= effective_on
      AND (version.effective_to IS NULL OR effective_on < version.effective_to)
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'no current PositionVersion covers the requested effective date'
            USING ERRCODE = '23503';
    END IF;
    IF predecessor.position_record_version_id <> p_expected_predecessor_version_id
       OR predecessor.position_status_code <> current_status THEN
        RAISE EXCEPTION 'reviewed Position state is stale at authoritative application time'
            USING ERRCODE = '40001';
    END IF;

    IF NOT validate_position_lifecycle_review_evidence(
        p_canonical_review_json,
        p_review_digest,
        p_tenant_record_id,
        p_position_record_id,
        current_status,
        proposed_status,
        effective_on
    ) THEN
        RAISE EXCEPTION 'position lifecycle review evidence is invalid or out of scope'
            USING ERRCODE = '23514';
    END IF;

    IF proposed_status IN ('closed', 'abolished')
       AND EXISTS (
            SELECT 1
            FROM public.assignment_record AS assignment
            WHERE assignment.tenant_record_id = p_tenant_record_id
              AND assignment.position_record_id = p_position_record_id
              AND assignment.recorded_from <= pg_catalog.transaction_timestamp()
              AND (assignment.recorded_to IS NULL OR pg_catalog.transaction_timestamp() < assignment.recorded_to)
              AND daterange(assignment.effective_from, assignment.effective_to, '[)')
                  && daterange(effective_on, NULL, '[)')
       ) THEN
        RAISE EXCEPTION 'Position cannot close or be abolished while a current Assignment crosses the effective date'
            USING ERRCODE = '23514';
    END IF;

    event_json := pg_catalog.jsonb_build_object(
        'data', pg_catalog.jsonb_build_object(
            'high_impact', true,
            'result_code', 'position_lifecycle_changed'
        ),
        'datacontenttype', 'application/json',
        'id', p_audit_event_record_id::text,
        'orgmetraactor', p_applied_by_actor_reference,
        'orgmetraconfirmation', 'human_confirmation:' || review_reference::text,
        'orgmetraevidence', p_review_digest,
        'orgmetrapurpose', 'position_lifecycle_change',
        'orgmetrareason', reason,
        'orgmetratenant', p_tenant_record_id::text,
        'source', 'urn:orgmetra:people_api',
        'specversion', '1.0',
        'subject', 'position_record:' || p_position_record_id::text,
        'time', to_char(
            pg_catalog.transaction_timestamp() AT TIME ZONE 'UTC',
            'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'
        ),
        'type', 'orgmetra.people.position_lifecycle_changed'
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

    INSERT INTO public.position_lifecycle_application_record (
        tenant_record_id,
        position_lifecycle_application_record_id,
        position_record_id,
        predecessor_position_record_version_id,
        successor_position_record_version_id,
        position_lifecycle_change_reference,
        canonical_review_json,
        review_evidence_digest_sha256,
        requester_actor_reference,
        reviewer_actor_reference,
        applied_by_actor_reference,
        current_status_code,
        proposed_status_code,
        reason_code,
        effective_on,
        reviewed_at,
        review_packet_recorded_at,
        audit_event_record_id,
        outbox_delivery_record_id
    ) VALUES (
        p_tenant_record_id,
        p_application_record_id,
        p_position_record_id,
        predecessor.position_record_version_id,
        p_successor_version_id,
        review_reference,
        p_canonical_review_json,
        p_review_digest,
        requester,
        reviewer,
        p_applied_by_actor_reference,
        current_status,
        proposed_status,
        reason,
        effective_on,
        reviewed_at,
        review_recorded_at,
        p_audit_event_record_id,
        p_outbox_delivery_record_id
    );

    UPDATE public.position_record_version
    SET recorded_to = pg_catalog.transaction_timestamp()
    WHERE tenant_record_id = p_tenant_record_id
      AND position_record_version_id = predecessor.position_record_version_id;

    IF predecessor.effective_from < effective_on THEN
        preserved_version_id := pg_catalog.gen_random_uuid();
        INSERT INTO public.position_record_version (
            tenant_record_id,
            position_record_version_id,
            position_record_id,
            position_status_code,
            effective_from,
            effective_to,
            recorded_from,
            position_lifecycle_application_record_id
        ) VALUES (
            p_tenant_record_id,
            preserved_version_id,
            p_position_record_id,
            predecessor.position_status_code,
            predecessor.effective_from,
            effective_on,
            pg_catalog.transaction_timestamp(),
            p_application_record_id
        );
    END IF;

    INSERT INTO public.position_record_version (
        tenant_record_id,
        position_record_version_id,
        position_record_id,
        position_status_code,
        effective_from,
        effective_to,
        recorded_from,
        position_lifecycle_application_record_id
    ) VALUES (
        p_tenant_record_id,
        p_successor_version_id,
        p_position_record_id,
        proposed_status,
        effective_on,
        predecessor.effective_to,
        pg_catalog.transaction_timestamp(),
        p_application_record_id
    );
END;
$$;

COMMENT ON FUNCTION public.apply_position_lifecycle_change(uuid, uuid, uuid, uuid, uuid, text, text, text, uuid, uuid) IS
    'Atomically validates one approved v1 lifecycle review against locked bitemporal Position/Assignment truth, records immutable audit/outbox evidence, closes the predecessor system-time interval, and inserts preserved/successor PositionVersion truth.';

ALTER TABLE position_lifecycle_application_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE position_lifecycle_application_record FORCE ROW LEVEL SECURITY;
CREATE POLICY position_lifecycle_application_scope_policy
ON public.position_lifecycle_application_record
USING (tenant_record_id = public.current_tenant_record_id())
WITH CHECK (tenant_record_id = public.current_tenant_record_id());

REVOKE ALL ON FUNCTION public.apply_position_lifecycle_change(
    uuid, uuid, uuid, uuid, uuid, text, text, text, uuid, uuid
) FROM PUBLIC;

COMMIT;
