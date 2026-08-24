-- Persist authoritative Position-to-Position solid-line reporting truth after
-- independent human review and authoritative application. Person, Assignment,
-- compensation, assessment, and free-form HR values remain outside this model.

CREATE TABLE position_reporting_relationship_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    position_reporting_relationship_record_id uuid PRIMARY KEY,
    subordinate_position_record_id uuid NOT NULL,
    relationship_type_code text NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    recorded_to timestamptz,
    CONSTRAINT position_reporting_relationship_record_id_operational_check
        CHECK (public.is_operational_uuid(position_reporting_relationship_record_id)),
    CONSTRAINT position_reporting_subordinate_tenant_fk
        FOREIGN KEY (tenant_record_id, subordinate_position_record_id)
        REFERENCES position_record(tenant_record_id, position_record_id),
    CONSTRAINT position_reporting_relationship_type_check
        CHECK (relationship_type_code = 'solid_line'),
    CONSTRAINT position_reporting_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT position_reporting_record_tenant_identity_unique
        UNIQUE (tenant_record_id, position_reporting_relationship_record_id),
    CONSTRAINT position_reporting_subordinate_type_unique
        UNIQUE (tenant_record_id, subordinate_position_record_id, relationship_type_code)
);

CREATE TABLE position_reporting_relationship_version (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    position_reporting_relationship_version_id uuid PRIMARY KEY,
    position_reporting_relationship_record_id uuid NOT NULL,
    manager_position_record_id uuid NOT NULL,
    review_evidence_digest_sha256 text NOT NULL,
    application_evidence_digest_sha256 text NOT NULL,
    reviewer_actor_reference text NOT NULL,
    applied_by_actor_reference text NOT NULL,
    reviewed_at timestamptz NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    recorded_to timestamptz,
    audit_event_record_id uuid NOT NULL,
    application_state text NOT NULL DEFAULT 'applied_after_human_review',
    CONSTRAINT position_reporting_version_id_operational_check
        CHECK (public.is_operational_uuid(position_reporting_relationship_version_id)),
    CONSTRAINT position_reporting_version_record_tenant_fk
        FOREIGN KEY (tenant_record_id, position_reporting_relationship_record_id)
        REFERENCES position_reporting_relationship_record(
            tenant_record_id,
            position_reporting_relationship_record_id
        ),
    CONSTRAINT position_reporting_manager_tenant_fk
        FOREIGN KEY (tenant_record_id, manager_position_record_id)
        REFERENCES position_record(tenant_record_id, position_record_id),
    CONSTRAINT position_reporting_audit_tenant_fk
        FOREIGN KEY (tenant_record_id, audit_event_record_id)
        REFERENCES audit_event_record(tenant_record_id, audit_event_record_id),
    CONSTRAINT position_reporting_review_digest_check
        CHECK (review_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT position_reporting_application_digest_check
        CHECK (application_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT position_reporting_reviewer_actor_check
        CHECK (
            reviewer_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT position_reporting_applied_actor_check
        CHECK (
            applied_by_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT position_reporting_actor_separation_check
        CHECK (reviewer_actor_reference <> applied_by_actor_reference),
    CONSTRAINT position_reporting_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT position_reporting_version_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT position_reporting_review_chronology_check
        CHECK (reviewed_at <= recorded_from),
    CONSTRAINT position_reporting_application_state_check
        CHECK (application_state = 'applied_after_human_review'),
    CONSTRAINT position_reporting_version_tenant_identity_unique
        UNIQUE (tenant_record_id, position_reporting_relationship_version_id),
    CONSTRAINT position_reporting_audit_event_unique
        UNIQUE (tenant_record_id, audit_event_record_id),
    CONSTRAINT position_reporting_bitemporal_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            position_reporting_relationship_record_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE FUNCTION enforce_position_reporting_system_time()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.recorded_to IS NOT NULL THEN
        RAISE EXCEPTION 'position-reporting recorded_to must be NULL on insert'
            USING ERRCODE = '22023';
    END IF;
    IF NEW.recorded_from IS DISTINCT FROM pg_catalog.transaction_timestamp() THEN
        RAISE EXCEPTION 'position-reporting recorded_from must equal the current transaction timestamp'
            USING ERRCODE = '22023';
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION enforce_position_reporting_system_time() IS
    'Requires PostgreSQL transaction time for new position-reporting recorded intervals and requires those intervals to begin open.';

CREATE TRIGGER position_reporting_record_system_time_guard
BEFORE INSERT ON position_reporting_relationship_record
FOR EACH ROW
EXECUTE FUNCTION enforce_position_reporting_system_time();

CREATE TRIGGER position_reporting_version_system_time_guard
BEFORE INSERT ON position_reporting_relationship_version
FOR EACH ROW
EXECUTE FUNCTION enforce_position_reporting_system_time();

CREATE FUNCTION protect_position_reporting_history()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'position-reporting history cannot be deleted'
            USING ERRCODE = '55000';
    END IF;

    IF OLD.recorded_to IS NOT NULL
       OR NEW.recorded_to IS NULL
       OR NEW.recorded_to IS DISTINCT FROM pg_catalog.transaction_timestamp()
       OR to_jsonb(NEW) - 'recorded_to' <> to_jsonb(OLD) - 'recorded_to' THEN
        RAISE EXCEPTION 'position-reporting history may only close an open recorded interval at the current transaction timestamp'
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION protect_position_reporting_history() IS
    'Rejects deletion and in-place rewriting of position-reporting history; UPDATE may only close an open system-recorded interval at PostgreSQL transaction time.';

CREATE TRIGGER position_reporting_record_history_guard
BEFORE UPDATE OR DELETE ON position_reporting_relationship_record
FOR EACH ROW
EXECUTE FUNCTION protect_position_reporting_history();

CREATE TRIGGER position_reporting_version_history_guard
BEFORE UPDATE OR DELETE ON position_reporting_relationship_version
FOR EACH ROW
EXECUTE FUNCTION protect_position_reporting_history();

CREATE FUNCTION enforce_position_reporting_scope()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    subordinate_position_id uuid;
    relationship_type text;
    anchor_recorded_to timestamptz;
    audit_event jsonb;
    audit_event_digest text;
    outbox_found boolean;
    cycle_found boolean;
BEGIN
    SELECT subordinate_position_record_id, relationship_type_code, recorded_to
    INTO subordinate_position_id, relationship_type, anchor_recorded_to
    FROM position_reporting_relationship_record
    WHERE tenant_record_id = NEW.tenant_record_id
      AND position_reporting_relationship_record_id = NEW.position_reporting_relationship_record_id
    FOR SHARE;

    IF NOT FOUND OR anchor_recorded_to IS NOT NULL THEN
        RAISE EXCEPTION 'position-reporting version requires an open same-tenant relationship anchor'
            USING ERRCODE = '23514';
    END IF;
    IF relationship_type <> 'solid_line' THEN
        RAISE EXCEPTION 'position-reporting persistence supports only solid-line relationships'
            USING ERRCODE = '23514';
    END IF;
    IF subordinate_position_id = NEW.manager_position_record_id THEN
        RAISE EXCEPTION 'a Position cannot report to itself'
            USING ERRCODE = '23514';
    END IF;

    WITH RECURSIVE manager_path(position_record_id, effective_period) AS (
        SELECT
            NEW.manager_position_record_id,
            daterange(NEW.effective_from, NEW.effective_to, '[)')
        UNION
        SELECT
            next_version.manager_position_record_id,
            manager_path.effective_period *
                daterange(next_version.effective_from, next_version.effective_to, '[)')
        FROM manager_path
        JOIN position_reporting_relationship_record AS next_record
          ON next_record.tenant_record_id = NEW.tenant_record_id
         AND next_record.subordinate_position_record_id = manager_path.position_record_id
         AND next_record.relationship_type_code = 'solid_line'
         AND next_record.recorded_to IS NULL
        JOIN position_reporting_relationship_version AS next_version
          ON next_version.tenant_record_id = next_record.tenant_record_id
         AND next_version.position_reporting_relationship_record_id =
             next_record.position_reporting_relationship_record_id
         AND next_version.recorded_to IS NULL
        WHERE manager_path.effective_period &&
              daterange(next_version.effective_from, next_version.effective_to, '[)')
    )
    SELECT EXISTS (
        SELECT 1
        FROM manager_path
        WHERE position_record_id = subordinate_position_id
    ) INTO cycle_found;

    IF cycle_found THEN
        RAISE EXCEPTION 'position-reporting relationship would create a management cycle'
            USING ERRCODE = '23514';
    END IF;

    SELECT canonical_event_json::jsonb, event_envelope_digest
    INTO audit_event, audit_event_digest
    FROM audit_event_record
    WHERE tenant_record_id = NEW.tenant_record_id
      AND audit_event_record_id = NEW.audit_event_record_id
    FOR SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'position-reporting version requires immutable same-tenant audit evidence'
            USING ERRCODE = '23514';
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM outbox_delivery_record
        WHERE tenant_record_id = NEW.tenant_record_id
          AND audit_event_record_id = NEW.audit_event_record_id
          AND delivery_target_code = 'integration_hub'
    ) INTO outbox_found;

    IF NOT outbox_found THEN
        RAISE EXCEPTION 'position-reporting version requires transactional audit/outbox evidence'
            USING ERRCODE = '23514';
    END IF;

    IF audit_event ->> 'orgmetrapurpose'
          IS DISTINCT FROM 'position_reporting_change_apply'
       OR audit_event ->> 'orgmetraactor'
          IS DISTINCT FROM NEW.applied_by_actor_reference
       OR audit_event ->> 'orgmetraevidence'
          IS DISTINCT FROM NEW.review_evidence_digest_sha256
       OR audit_event_digest IS DISTINCT FROM NEW.application_evidence_digest_sha256
       OR audit_event ->> 'subject'
          IS DISTINCT FROM
             'position_reporting_relationship:' || NEW.position_reporting_relationship_record_id::text
       OR audit_event #>> '{data,result_code}'
          IS DISTINCT FROM 'position_reporting_applied'
       OR (audit_event #>> '{data,high_impact}')::boolean IS DISTINCT FROM false
       OR (audit_event ->> 'time')::timestamptz < NEW.reviewed_at
       OR (audit_event ->> 'time')::timestamptz > NEW.recorded_from THEN
        RAISE EXCEPTION 'position-reporting audit evidence does not exactly match the applied relationship scope'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION enforce_position_reporting_scope() IS
    'Before persistence, resolves the same-tenant relationship anchor, rejects self-reporting and cycles over overlapping effective time, and requires immutable audit/outbox application evidence that binds the reviewed evidence digest, applying actor, exact application event digest, subject, result, and chronology.';

CREATE TRIGGER position_reporting_version_scope_guard
BEFORE INSERT ON position_reporting_relationship_version
FOR EACH ROW
EXECUTE FUNCTION enforce_position_reporting_scope();

CREATE FUNCTION enforce_position_reporting_anchor_alignment()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.recorded_to IS NULL OR NEW.recorded_to IS NOT DISTINCT FROM OLD.recorded_to THEN
        RETURN NULL;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM position_reporting_relationship_version AS version
        WHERE version.tenant_record_id = NEW.tenant_record_id
          AND version.position_reporting_relationship_record_id =
              NEW.position_reporting_relationship_record_id
          AND (version.recorded_to IS NULL OR version.recorded_to > NEW.recorded_to)
    ) THEN
        RAISE EXCEPTION 'cannot close position-reporting anchor while a recorded version remains open'
            USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION enforce_position_reporting_anchor_alignment() IS
    'Deferred anchor-closure guard: every relationship version must be recorded closed no later than its durable anchor before commit.';

CREATE CONSTRAINT TRIGGER position_reporting_anchor_alignment_guard
AFTER UPDATE ON position_reporting_relationship_record
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION enforce_position_reporting_anchor_alignment();

CREATE FUNCTION reject_position_reporting_truncate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'position-reporting history cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION reject_position_reporting_truncate() IS
    'Rejects table-wide TRUNCATE so position-reporting history cannot bypass row-level bitemporal guards.';

CREATE TRIGGER position_reporting_record_truncate_guard
BEFORE TRUNCATE ON position_reporting_relationship_record
FOR EACH STATEMENT
EXECUTE FUNCTION reject_position_reporting_truncate();

CREATE TRIGGER position_reporting_version_truncate_guard
BEFORE TRUNCATE ON position_reporting_relationship_version
FOR EACH STATEMENT
EXECUTE FUNCTION reject_position_reporting_truncate();

REVOKE TRUNCATE ON position_reporting_relationship_record FROM PUBLIC;
REVOKE TRUNCATE ON position_reporting_relationship_version FROM PUBLIC;

ALTER TABLE position_reporting_relationship_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE position_reporting_relationship_record FORCE ROW LEVEL SECURITY;
CREATE POLICY position_reporting_record_scope_policy
ON position_reporting_relationship_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE position_reporting_relationship_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE position_reporting_relationship_version FORCE ROW LEVEL SECURITY;
CREATE POLICY position_reporting_version_scope_policy
ON position_reporting_relationship_version
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

COMMENT ON TABLE position_reporting_relationship_record IS
    'Durable tenant-scoped Position-to-Position solid-line relationship anchor. The subordinate seat and relationship type are stable anchor identity; Person and Assignment are intentionally absent.';

COMMENT ON TABLE position_reporting_relationship_version IS
    'Authoritative bitemporal manager-Position versions applied only after separate human review and immutable audit/outbox evidence. The application audit event must bind the review digest and its exact envelope digest. The relation stores no worker PII, compensation, ratings, or employment-decision output.';
