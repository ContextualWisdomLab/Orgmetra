-- Persist reason-free Employment absence truth inside the authoritative HRIS core.
-- Sensitive leave-case reasons remain outside this relation. Audit/outbox references
-- are opaque contract correlations; this migration does not query foreign services.

CREATE TABLE employment_absence_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    employment_absence_record_id uuid PRIMARY KEY,
    employment_record_id uuid NOT NULL,
    person_record_id uuid NOT NULL,
    created_by_actor_reference text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),

    CONSTRAINT employment_absence_record_id_operational_check
        CHECK (public.is_operational_uuid(employment_absence_record_id)),
    CONSTRAINT employment_absence_employment_person_tenant_fk
        FOREIGN KEY (tenant_record_id, employment_record_id, person_record_id)
        REFERENCES employment_record(tenant_record_id, employment_record_id, person_record_id),
    CONSTRAINT employment_absence_created_actor_reference_check
        CHECK (
            created_by_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT employment_absence_record_tenant_identity_unique
        UNIQUE (tenant_record_id, employment_absence_record_id)
);

COMMENT ON TABLE public.employment_absence_record IS
    'Stable tenant-qualified identity for one reason-free Employment absence fact. Sensitive leave reasons and employment-decision authority are intentionally absent.';

CREATE TABLE employment_absence_version (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    employment_absence_version_id uuid PRIMARY KEY,
    employment_absence_record_id uuid NOT NULL,
    absence_status_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    source_evidence_digest_sha256 text NOT NULL,
    audit_event_reference text NOT NULL,
    outbox_event_reference text NOT NULL,
    application_evidence_digest_sha256 text NOT NULL,
    application_purpose_code text NOT NULL DEFAULT 'employment_absence_record',
    application_reason_code text NOT NULL DEFAULT 'operational_absence_fact',
    decision_authority_state text NOT NULL DEFAULT 'not_authorized_for_employment_decision',
    evidence_version integer NOT NULL DEFAULT 1,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    recorded_to timestamptz,

    CONSTRAINT employment_absence_version_id_operational_check
        CHECK (public.is_operational_uuid(employment_absence_version_id)),
    CONSTRAINT employment_absence_version_record_tenant_fk
        FOREIGN KEY (tenant_record_id, employment_absence_record_id)
        REFERENCES employment_absence_record(tenant_record_id, employment_absence_record_id),
    CONSTRAINT employment_absence_status_code_check
        CHECK (absence_status_code IN ('confirmed', 'cancelled')),
    CONSTRAINT employment_absence_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT employment_absence_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT employment_absence_source_digest_check
        CHECK (source_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT employment_absence_audit_reference_check
        CHECK (
            audit_event_reference ~
            '^audit_event:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT employment_absence_outbox_reference_check
        CHECK (
            outbox_event_reference ~
            '^outbox_event:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT employment_absence_application_digest_check
        CHECK (application_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT employment_absence_application_purpose_check
        CHECK (application_purpose_code = 'employment_absence_record'),
    CONSTRAINT employment_absence_application_reason_check
        CHECK (application_reason_code = 'operational_absence_fact'),
    CONSTRAINT employment_absence_decision_authority_check
        CHECK (decision_authority_state = 'not_authorized_for_employment_decision'),
    CONSTRAINT employment_absence_evidence_version_check
        CHECK (evidence_version = 1),
    CONSTRAINT employment_absence_version_tenant_identity_unique
        UNIQUE (tenant_record_id, employment_absence_version_id),
    CONSTRAINT employment_absence_version_bitemporal_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            employment_absence_record_id WITH =,
            pg_catalog.daterange(effective_from, effective_to, '[)') WITH &&,
            pg_catalog.tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

COMMENT ON TABLE public.employment_absence_version IS
    'Bitemporal, reason-free status history for one Employment absence identity. confirmed/cancelled are operational facts only and never authorize an employment decision.';

CREATE FUNCTION public.enforce_employment_absence_anchor_system_time()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    IF NEW.created_at IS DISTINCT FROM pg_catalog.transaction_timestamp() THEN
        RAISE EXCEPTION 'employment-absence created_at must equal the current transaction timestamp'
            USING ERRCODE = '22023';
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.enforce_employment_absence_anchor_system_time() IS
    'Prevents caller-backdated system creation time on the durable absence identity.';

CREATE TRIGGER employment_absence_anchor_system_time_guard
BEFORE INSERT ON public.employment_absence_record
FOR EACH ROW
EXECUTE FUNCTION public.enforce_employment_absence_anchor_system_time();

CREATE FUNCTION public.employment_absence_has_staffable_coverage(
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
        pg_catalog.daterange(requested_effective_from, requested_effective_to, '[)') <@
        pg_catalog.range_agg(pg_catalog.daterange(
            employment_version.effective_from,
            employment_version.effective_to,
            '[)'
        )),
        false
    )
    FROM public.employment_record_version AS employment_version
    WHERE employment_version.tenant_record_id = requested_tenant_id
      AND employment_version.employment_record_id = requested_employment_id
      AND employment_version.employment_status_code IN ('active', 'leave')
      AND employment_version.recorded_from <= requested_known_at
      AND (
          employment_version.recorded_to IS NULL
          OR employment_version.recorded_to > requested_known_at
      );
$$;

COMMENT ON FUNCTION public.employment_absence_has_staffable_coverage(uuid, uuid, date, date, timestamptz) IS
    'Requires current system-visible active/leave Employment versions to cover the complete proposed absence business interval.';

CREATE FUNCTION public.validate_employment_absence_version_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    absence_employment_id uuid;
    insertion_time timestamptz := pg_catalog.transaction_timestamp();
BEGIN
    IF NEW.recorded_from IS DISTINCT FROM insertion_time OR NEW.recorded_to IS NOT NULL THEN
        RAISE EXCEPTION 'employment-absence recorded_from must equal transaction time and recorded_to must start open'
            USING ERRCODE = '22023';
    END IF;

    SELECT absence_record.employment_record_id
    INTO absence_employment_id
    FROM public.employment_absence_record AS absence_record
    WHERE absence_record.tenant_record_id = NEW.tenant_record_id
      AND absence_record.employment_absence_record_id = NEW.employment_absence_record_id;

    IF absence_employment_id IS NULL THEN
        RAISE EXCEPTION 'employment-absence anchor is missing from the requested tenant'
            USING ERRCODE = '23503';
    END IF;

    -- Serialize mutations for one tenant-qualified Employment. Hash collisions only
    -- over-serialize; they cannot weaken the invariant.
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(
            NEW.tenant_record_id::text || ':' || absence_employment_id::text,
            0
        )
    );

    IF NEW.absence_status_code = 'confirmed'
       AND NOT public.employment_absence_has_staffable_coverage(
        NEW.tenant_record_id,
        absence_employment_id,
        NEW.effective_from,
        NEW.effective_to,
        insertion_time
    ) THEN
        RAISE EXCEPTION 'employment-absence requires active or leave Employment coverage for the complete effective interval'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.absence_status_code = 'confirmed' AND EXISTS (
        SELECT 1
        FROM public.employment_absence_record AS other_record
        JOIN public.employment_absence_version AS other_version
          ON other_version.tenant_record_id = other_record.tenant_record_id
         AND other_version.employment_absence_record_id = other_record.employment_absence_record_id
        WHERE other_record.tenant_record_id = NEW.tenant_record_id
          AND other_record.employment_record_id = absence_employment_id
          AND other_record.employment_absence_record_id <> NEW.employment_absence_record_id
          AND other_version.absence_status_code = 'confirmed'
          AND other_version.recorded_from <= insertion_time
          AND (other_version.recorded_to IS NULL OR other_version.recorded_to > insertion_time)
          AND pg_catalog.daterange(other_version.effective_from, other_version.effective_to, '[)') &&
              pg_catalog.daterange(NEW.effective_from, NEW.effective_to, '[)')
    ) THEN
        RAISE EXCEPTION 'a confirmed absence already exists for this Employment and effective interval'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.validate_employment_absence_version_insert() IS
    'Validates database-owned system time, confirmed-absence active/leave Employment coverage, and serialized single-confirmed-absence truth before insert.';

CREATE TRIGGER employment_absence_version_insert_guard
BEFORE INSERT ON public.employment_absence_version
FOR EACH ROW
EXECUTE FUNCTION public.validate_employment_absence_version_insert();

CREATE FUNCTION public.protect_employment_absence_anchor_immutability()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'employment-absence identity is immutable'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION public.protect_employment_absence_anchor_immutability() IS
    'Rejects UPDATE and DELETE on stable absence identities; corrections belong in version history.';

CREATE TRIGGER employment_absence_anchor_immutability_guard
BEFORE UPDATE OR DELETE ON public.employment_absence_record
FOR EACH ROW
EXECUTE FUNCTION public.protect_employment_absence_anchor_immutability();

CREATE FUNCTION public.protect_employment_absence_version_history()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'employment-absence history is immutable'
            USING ERRCODE = '55000';
    END IF;

    IF OLD.recorded_to IS NULL
       AND NEW.recorded_to IS NOT NULL
       AND NEW.recorded_to IS NOT DISTINCT FROM pg_catalog.transaction_timestamp()
       AND (pg_catalog.to_jsonb(NEW) - 'recorded_to') = (pg_catalog.to_jsonb(OLD) - 'recorded_to') THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION 'employment-absence history is immutable except for database-time closure'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION public.protect_employment_absence_version_history() IS
    'Allows only one correction-not-rewrite transition: closing an open recorded interval at the current transaction timestamp.';

CREATE TRIGGER employment_absence_version_history_guard
BEFORE UPDATE OR DELETE ON public.employment_absence_version
FOR EACH ROW
EXECUTE FUNCTION public.protect_employment_absence_version_history();

CREATE FUNCTION public.reject_employment_absence_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'employment-absence history cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION public.reject_employment_absence_truncate() IS
    'Rejects table-wide TRUNCATE so reason-free absence history cannot bypass row-level immutability.';

CREATE TRIGGER employment_absence_record_truncate_guard
BEFORE TRUNCATE ON public.employment_absence_record
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_employment_absence_truncate();

CREATE TRIGGER employment_absence_version_truncate_guard
BEFORE TRUNCATE ON public.employment_absence_version
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_employment_absence_truncate();

REVOKE TRUNCATE ON public.employment_absence_record FROM PUBLIC;
REVOKE TRUNCATE ON public.employment_absence_version FROM PUBLIC;

ALTER TABLE employment_absence_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE employment_absence_record FORCE ROW LEVEL SECURITY;
ALTER TABLE employment_absence_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE employment_absence_version FORCE ROW LEVEL SECURITY;

CREATE POLICY employment_absence_record_tenant_isolation_policy
ON public.employment_absence_record
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

CREATE POLICY employment_absence_version_tenant_isolation_policy
ON public.employment_absence_version
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
