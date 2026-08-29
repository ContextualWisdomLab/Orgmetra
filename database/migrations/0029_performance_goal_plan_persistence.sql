-- Persist activated performance-goal plan truth inside Orgmetra's authoritative HRIS core.
-- The relations deliberately exclude goal text, ratings, assessment scores, compensation,
-- candidate data, prompts and model output. Activation remains non-authorizing for ratings
-- and employment decisions; immutable audit/outbox evidence is required before persistence.

CREATE TABLE performance_goal_plan_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    performance_goal_plan_record_id uuid PRIMARY KEY,
    performance_goal_plan_reference text NOT NULL,
    employment_record_id uuid NOT NULL,
    job_profile_id uuid NOT NULL,
    performance_cycle_reference text NOT NULL,
    created_by_actor_reference text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),

    CONSTRAINT performance_goal_plan_record_id_operational_check
        CHECK (public.is_operational_uuid(performance_goal_plan_record_id)),
    CONSTRAINT performance_goal_plan_employment_tenant_fk
        FOREIGN KEY (tenant_record_id, employment_record_id)
        REFERENCES employment_record(tenant_record_id, employment_record_id),
    CONSTRAINT performance_goal_plan_job_tenant_fk
        FOREIGN KEY (tenant_record_id, job_profile_id)
        REFERENCES job_profile(tenant_record_id, job_profile_id),
    CONSTRAINT performance_goal_plan_reference_check
        CHECK (
            performance_goal_plan_reference ~
            '^performance_goal_plan:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT performance_goal_plan_cycle_reference_check
        CHECK (
            performance_cycle_reference ~
            '^performance_cycle:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT performance_goal_plan_created_actor_reference_check
        CHECK (
            created_by_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT performance_goal_plan_tenant_identity_unique
        UNIQUE (tenant_record_id, performance_goal_plan_record_id),
    CONSTRAINT performance_goal_plan_reference_unique
        UNIQUE (tenant_record_id, performance_goal_plan_reference)
);

COMMENT ON TABLE performance_goal_plan_record IS
    'Stable tenant-qualified identity for one activated performance-goal plan, bound to one Employment, Job and performance cycle without storing goal text or ratings.';

CREATE TABLE performance_goal_plan_version (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    performance_goal_plan_version_id uuid PRIMARY KEY,
    performance_goal_plan_record_id uuid NOT NULL,
    goal_set_digest_sha256 text NOT NULL,
    measurement_definition_digest_sha256 text NOT NULL,
    goal_count integer NOT NULL,
    feedback_cadence_code text NOT NULL,
    plan_evidence_digest_sha256 text NOT NULL,
    activation_reference text NOT NULL,
    activation_evidence_digest_sha256 text NOT NULL,
    authority_evidence_reference text NOT NULL,
    authority_evidence_digest_sha256 text NOT NULL,
    approving_actor_reference text NOT NULL,
    approved_at timestamptz NOT NULL,
    activated_at timestamptz NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    audit_event_record_id uuid NOT NULL,
    persistence_state text NOT NULL DEFAULT 'authoritatively_persisted',
    rating_authority_state text NOT NULL DEFAULT 'not_authorized_for_performance_rating',
    employment_decision_authority_state text NOT NULL DEFAULT 'not_authorized_for_employment_decision',
    evidence_version integer NOT NULL DEFAULT 1,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    recorded_to timestamptz,

    CONSTRAINT performance_goal_plan_version_id_operational_check
        CHECK (public.is_operational_uuid(performance_goal_plan_version_id)),
    CONSTRAINT performance_goal_plan_version_record_tenant_fk
        FOREIGN KEY (tenant_record_id, performance_goal_plan_record_id)
        REFERENCES performance_goal_plan_record(tenant_record_id, performance_goal_plan_record_id),
    CONSTRAINT performance_goal_plan_version_audit_tenant_fk
        FOREIGN KEY (tenant_record_id, audit_event_record_id)
        REFERENCES audit_event_record(tenant_record_id, audit_event_record_id),
    CONSTRAINT performance_goal_plan_goal_set_digest_check
        CHECK (goal_set_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT performance_goal_plan_measurement_digest_check
        CHECK (measurement_definition_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT performance_goal_plan_count_check
        CHECK (goal_count BETWEEN 1 AND 20),
    CONSTRAINT performance_goal_plan_feedback_cadence_check
        CHECK (feedback_cadence_code IN (
            'continuous_feedback',
            'monthly_check_in',
            'quarterly_check_in'
        )),
    CONSTRAINT performance_goal_plan_plan_digest_check
        CHECK (plan_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT performance_goal_plan_activation_reference_check
        CHECK (
            activation_reference ~
            '^performance_goal_activation:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT performance_goal_plan_activation_digest_check
        CHECK (activation_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT performance_goal_plan_authority_reference_check
        CHECK (
            authority_evidence_reference ~
            '^performance_goal_authority:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT performance_goal_plan_authority_digest_check
        CHECK (authority_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT performance_goal_plan_approving_actor_check
        CHECK (
            approving_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT performance_goal_plan_approval_chronology_check
        CHECK (activated_at >= approved_at),
    CONSTRAINT performance_goal_plan_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT performance_goal_plan_no_retroactive_activation_check
        CHECK (effective_from >= approved_at::date),
    CONSTRAINT performance_goal_plan_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT performance_goal_plan_persistence_state_check
        CHECK (persistence_state = 'authoritatively_persisted'),
    CONSTRAINT performance_goal_plan_rating_authority_check
        CHECK (rating_authority_state = 'not_authorized_for_performance_rating'),
    CONSTRAINT performance_goal_plan_employment_decision_authority_check
        CHECK (employment_decision_authority_state = 'not_authorized_for_employment_decision'),
    CONSTRAINT performance_goal_plan_evidence_version_check
        CHECK (evidence_version = 1),
    CONSTRAINT performance_goal_plan_version_tenant_identity_unique
        UNIQUE (tenant_record_id, performance_goal_plan_version_id),
    CONSTRAINT performance_goal_plan_activation_unique
        UNIQUE (tenant_record_id, activation_reference),
    CONSTRAINT performance_goal_plan_audit_unique
        UNIQUE (tenant_record_id, audit_event_record_id),
    CONSTRAINT performance_goal_plan_bitemporal_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            performance_goal_plan_record_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

COMMENT ON TABLE performance_goal_plan_version IS
    'Bitemporal activated goal-plan evidence. Digests, cadence and activation provenance are durable; goal text, ratings and employment-decision authority remain outside this relation.';

CREATE FUNCTION enforce_performance_goal_plan_anchor_system_time()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    IF NEW.created_at IS DISTINCT FROM pg_catalog.transaction_timestamp() THEN
        RAISE EXCEPTION 'performance-goal plan created_at must equal the current transaction timestamp'
            USING ERRCODE = '22023';
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION enforce_performance_goal_plan_anchor_system_time() IS
    'Prevents caller-backdated system creation time on a durable performance-goal plan identity.';

CREATE TRIGGER performance_goal_plan_anchor_system_time_guard
BEFORE INSERT ON performance_goal_plan_record
FOR EACH ROW
EXECUTE FUNCTION enforce_performance_goal_plan_anchor_system_time();

CREATE FUNCTION performance_goal_plan_employment_has_coverage(
    requested_tenant_id uuid,
    requested_employment_id uuid,
    requested_effective_from date,
    requested_effective_to date,
    requested_known_at timestamptz
)
RETURNS boolean
LANGUAGE sql
STABLE
SET search_path = pg_catalog, public, pg_temp
AS $$
    SELECT COALESCE(
        daterange(requested_effective_from, requested_effective_to, '[)') <@
        pg_catalog.range_agg(daterange(
            employment_version.effective_from,
            employment_version.effective_to,
            '[)'
        )),
        false
    )
    FROM employment_record_version AS employment_version
    WHERE employment_version.tenant_record_id = requested_tenant_id
      AND employment_version.employment_record_id = requested_employment_id
      AND employment_version.employment_status_code IN ('active', 'leave')
      AND employment_version.recorded_from <= requested_known_at
      AND (
          employment_version.recorded_to IS NULL
          OR employment_version.recorded_to > requested_known_at
      );
$$;

COMMENT ON FUNCTION performance_goal_plan_employment_has_coverage(uuid, uuid, date, date, timestamptz) IS
    'Requires system-visible active/leave Employment versions to cover the complete goal-plan business interval.';

CREATE FUNCTION performance_goal_plan_job_has_coverage(
    requested_tenant_id uuid,
    requested_job_profile_id uuid,
    requested_effective_from date,
    requested_effective_to date,
    requested_known_at timestamptz
)
RETURNS boolean
LANGUAGE sql
STABLE
SET search_path = pg_catalog, public, pg_temp
AS $$
    SELECT COALESCE(
        daterange(requested_effective_from, requested_effective_to, '[)') <@
        pg_catalog.range_agg(daterange(
            job_version.effective_from,
            job_version.effective_to,
            '[)'
        )),
        false
    )
    FROM job_profile_version AS job_version
    WHERE job_version.tenant_record_id = requested_tenant_id
      AND job_version.job_profile_id = requested_job_profile_id
      AND job_version.recorded_from <= requested_known_at
      AND (
          job_version.recorded_to IS NULL
          OR job_version.recorded_to > requested_known_at
      );
$$;

COMMENT ON FUNCTION performance_goal_plan_job_has_coverage(uuid, uuid, date, date, timestamptz) IS
    'Requires system-visible Job versions to cover the complete goal-plan business interval.';

CREATE FUNCTION validate_performance_goal_plan_version_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    insertion_time timestamptz := pg_catalog.transaction_timestamp();
    anchor_plan_reference text;
    anchor_employment_id uuid;
    anchor_job_profile_id uuid;
    anchor_actor_reference text;
    employment_covered boolean;
    job_covered boolean;
    audit_event jsonb;
    outbox_found boolean;
BEGIN
    IF NEW.recorded_from IS DISTINCT FROM insertion_time OR NEW.recorded_to IS NOT NULL THEN
        RAISE EXCEPTION 'performance-goal plan recorded_from must equal transaction time and recorded_to must start open'
            USING ERRCODE = '22023';
    END IF;
    IF NEW.activated_at > insertion_time THEN
        RAISE EXCEPTION 'performance-goal plan activation cannot be recorded before activation occurred'
            USING ERRCODE = '22023';
    END IF;

    SELECT performance_goal_plan_reference, employment_record_id, job_profile_id,
           created_by_actor_reference
    INTO anchor_plan_reference, anchor_employment_id, anchor_job_profile_id,
         anchor_actor_reference
    FROM performance_goal_plan_record
    WHERE tenant_record_id = NEW.tenant_record_id
      AND performance_goal_plan_record_id = NEW.performance_goal_plan_record_id
    FOR SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'performance-goal plan version requires a same-tenant plan anchor'
            USING ERRCODE = '23514';
    END IF;

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(
            NEW.tenant_record_id::text || ':' || NEW.performance_goal_plan_record_id::text,
            0
        )
    );

    employment_covered := performance_goal_plan_employment_has_coverage(
        NEW.tenant_record_id,
        anchor_employment_id,
        NEW.effective_from,
        NEW.effective_to,
        insertion_time
    );
    job_covered := performance_goal_plan_job_has_coverage(
        NEW.tenant_record_id,
        anchor_job_profile_id,
        NEW.effective_from,
        NEW.effective_to,
        insertion_time
    );
    IF NOT employment_covered OR NOT job_covered THEN
        RAISE EXCEPTION 'performance-goal plan requires active or leave Employment coverage and authoritative Job coverage for the complete effective interval'
            USING ERRCODE = '23514';
    END IF;

    IF anchor_actor_reference IS DISTINCT FROM NEW.approving_actor_reference THEN
        RAISE EXCEPTION 'performance-goal plan approving actor must match the reviewed accountable actor'
            USING ERRCODE = '23514';
    END IF;

    SELECT canonical_event_json::jsonb
    INTO audit_event
    FROM audit_event_record
    WHERE tenant_record_id = NEW.tenant_record_id
      AND audit_event_record_id = NEW.audit_event_record_id
    FOR SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'performance-goal plan requires immutable same-tenant audit evidence'
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
        RAISE EXCEPTION 'performance-goal plan requires transactional audit/outbox evidence'
            USING ERRCODE = '23514';
    END IF;

    IF audit_event ->> 'orgmetratenant' IS DISTINCT FROM NEW.tenant_record_id::text
       OR audit_event ->> 'orgmetrapurpose' IS DISTINCT FROM 'performance_goal_plan_persistence'
       OR audit_event ->> 'orgmetrareason' IS DISTINCT FROM 'activated_goal_plan_record'
       OR audit_event ->> 'orgmetraactor' IS DISTINCT FROM NEW.approving_actor_reference
       OR audit_event ->> 'orgmetraevidence' IS DISTINCT FROM NEW.activation_evidence_digest_sha256
       OR audit_event ->> 'subject' IS DISTINCT FROM anchor_plan_reference
       OR audit_event #>> '{data,result_code}' IS DISTINCT FROM 'activated_plan_persisted'
       OR (audit_event #>> '{data,high_impact}')::boolean IS DISTINCT FROM false
       OR (audit_event ->> 'time')::timestamptz IS DISTINCT FROM NEW.activated_at THEN
        RAISE EXCEPTION 'performance-goal plan audit evidence does not match the activated plan scope'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION validate_performance_goal_plan_version_insert() IS
    'Before persistence, validates PostgreSQL-owned system time, complete Employment/Job business coverage, accountable actor binding, exact immutable activation audit evidence and transactional outbox correlation.';

CREATE TRIGGER performance_goal_plan_version_insert_guard
BEFORE INSERT ON performance_goal_plan_version
FOR EACH ROW
EXECUTE FUNCTION validate_performance_goal_plan_version_insert();

CREATE FUNCTION protect_performance_goal_plan_anchor_immutability()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'performance-goal plan identity is immutable'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION protect_performance_goal_plan_anchor_immutability() IS
    'Rejects UPDATE and DELETE on stable performance-goal plan identities; corrections belong in bitemporal version history.';

CREATE TRIGGER performance_goal_plan_anchor_immutability_guard
BEFORE UPDATE OR DELETE ON performance_goal_plan_record
FOR EACH ROW
EXECUTE FUNCTION protect_performance_goal_plan_anchor_immutability();

CREATE FUNCTION protect_performance_goal_plan_version_history()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'performance-goal plan history is immutable'
            USING ERRCODE = '55000';
    END IF;

    IF OLD.recorded_to IS NULL
       AND NEW.recorded_to IS NOT NULL
       AND NEW.recorded_to IS NOT DISTINCT FROM pg_catalog.transaction_timestamp()
       AND (pg_catalog.to_jsonb(NEW) - 'recorded_to') =
           (pg_catalog.to_jsonb(OLD) - 'recorded_to') THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION 'performance-goal plan history is immutable except for database-time closure'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION protect_performance_goal_plan_version_history() IS
    'Allows only one correction-not-rewrite transition: close an open recorded interval at PostgreSQL transaction time.';

CREATE TRIGGER performance_goal_plan_version_history_guard
BEFORE UPDATE OR DELETE ON performance_goal_plan_version
FOR EACH ROW
EXECUTE FUNCTION protect_performance_goal_plan_version_history();

CREATE FUNCTION reject_performance_goal_plan_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'performance-goal plan history cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION reject_performance_goal_plan_truncate() IS
    'Rejects table-wide TRUNCATE so plan evidence cannot bypass row-level immutability.';

CREATE TRIGGER performance_goal_plan_record_truncate_guard
BEFORE TRUNCATE ON performance_goal_plan_record
FOR EACH STATEMENT
EXECUTE FUNCTION reject_performance_goal_plan_truncate();

CREATE TRIGGER performance_goal_plan_version_truncate_guard
BEFORE TRUNCATE ON performance_goal_plan_version
FOR EACH STATEMENT
EXECUTE FUNCTION reject_performance_goal_plan_truncate();

REVOKE TRUNCATE ON performance_goal_plan_record FROM PUBLIC;
REVOKE TRUNCATE ON performance_goal_plan_version FROM PUBLIC;

ALTER TABLE performance_goal_plan_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_goal_plan_record FORCE ROW LEVEL SECURITY;
ALTER TABLE performance_goal_plan_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_goal_plan_version FORCE ROW LEVEL SECURITY;

CREATE POLICY performance_goal_plan_record_tenant_isolation_policy
ON performance_goal_plan_record
USING (
    tenant_record_id = NULLIF(
        pg_catalog.current_setting('orgmetra.tenant_record_id', true),
        ''
    )::uuid
)
WITH CHECK (
    tenant_record_id = NULLIF(
        pg_catalog.current_setting('orgmetra.tenant_record_id', true),
        ''
    )::uuid
);

CREATE POLICY performance_goal_plan_version_tenant_isolation_policy
ON performance_goal_plan_version
USING (
    tenant_record_id = NULLIF(
        pg_catalog.current_setting('orgmetra.tenant_record_id', true),
        ''
    )::uuid
)
WITH CHECK (
    tenant_record_id = NULLIF(
        pg_catalog.current_setting('orgmetra.tenant_record_id', true),
        ''
    )::uuid
);
