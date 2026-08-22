-- Make outbox retry delay an authoritative tenant/target policy instead of a
-- caller-selected transport parameter. Existing delivery-attempt budgets remain
-- owned by outbox_delivery_record; this migration only governs when retry work
-- becomes eligible again. Missing policy fails closed.

CREATE TABLE outbox_retry_policy_record (
    tenant_record_id uuid NOT NULL
        REFERENCES public.tenant_record(tenant_record_id),
    outbox_retry_policy_record_id uuid NOT NULL,
    delivery_target_code text NOT NULL,
    policy_version integer NOT NULL,
    base_delay_seconds integer NOT NULL,
    maximum_delay_seconds integer NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT transaction_timestamp(),
    recorded_to timestamptz,
    CONSTRAINT outbox_retry_policy_record_primary_key
        PRIMARY KEY (tenant_record_id, outbox_retry_policy_record_id),
    CONSTRAINT outbox_retry_policy_record_version_key
        UNIQUE (tenant_record_id, delivery_target_code, policy_version),
    CONSTRAINT outbox_retry_policy_record_identity_check
        CHECK (
            public.is_operational_uuid(tenant_record_id) IS TRUE
            AND public.is_operational_uuid(outbox_retry_policy_record_id) IS TRUE
        ),
    CONSTRAINT outbox_retry_policy_record_target_check
        CHECK (
            delivery_target_code COLLATE "C"
                ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$'
        ),
    CONSTRAINT outbox_retry_policy_record_version_check
        CHECK (policy_version BETWEEN 1 AND 2147483647),
    CONSTRAINT outbox_retry_policy_record_delay_check
        CHECK (
            base_delay_seconds BETWEEN 1 AND 86400
            AND maximum_delay_seconds BETWEEN base_delay_seconds AND 86400
        ),
    CONSTRAINT outbox_retry_policy_record_recorded_interval_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE UNIQUE INDEX outbox_retry_policy_active_target_index
ON public.outbox_retry_policy_record (tenant_record_id, delivery_target_code)
WHERE recorded_to IS NULL;

ALTER TABLE public.outbox_retry_policy_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outbox_retry_policy_record FORCE ROW LEVEL SECURITY;

CREATE POLICY outbox_retry_policy_tenant_isolation
ON public.outbox_retry_policy_record
USING (tenant_record_id = public.current_tenant_record_id())
WITH CHECK (tenant_record_id = public.current_tenant_record_id());

CREATE FUNCTION public.protect_outbox_retry_policy_record()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    latest_policy_version integer;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'outbox retry policy records cannot be deleted'
            USING ERRCODE = '55000';
    END IF;

    IF public.current_tenant_record_id() IS DISTINCT FROM NEW.tenant_record_id THEN
        RAISE EXCEPTION 'outbox retry policy tenant context does not match record tenant'
            USING ERRCODE = '42501';
    END IF;

    IF TG_OP = 'INSERT' THEN
        IF NEW.recorded_to IS NOT NULL
           OR NEW.recorded_from > transaction_timestamp() THEN
            RAISE EXCEPTION 'new outbox retry policy versions must be current system-recorded evidence'
                USING ERRCODE = '22023';
        END IF;

        SELECT max(policy_record.policy_version)
        INTO latest_policy_version
        FROM public.outbox_retry_policy_record AS policy_record
        WHERE policy_record.tenant_record_id = NEW.tenant_record_id
          AND policy_record.delivery_target_code = NEW.delivery_target_code;

        IF latest_policy_version IS NOT NULL
           AND NEW.policy_version <> latest_policy_version + 1 THEN
            RAISE EXCEPTION 'outbox retry policy version must advance exactly once'
                USING ERRCODE = '22023';
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.tenant_record_id <> OLD.tenant_record_id
       OR NEW.outbox_retry_policy_record_id <> OLD.outbox_retry_policy_record_id
       OR NEW.delivery_target_code <> OLD.delivery_target_code
       OR NEW.policy_version <> OLD.policy_version
       OR NEW.base_delay_seconds <> OLD.base_delay_seconds
       OR NEW.maximum_delay_seconds <> OLD.maximum_delay_seconds
       OR NEW.recorded_from <> OLD.recorded_from THEN
        RAISE EXCEPTION 'outbox retry policy identity and configured delay are immutable'
            USING ERRCODE = '55000';
    END IF;

    IF OLD.recorded_to IS NOT NULL
       OR NEW.recorded_to IS NULL
       OR NEW.recorded_to > transaction_timestamp() THEN
        RAISE EXCEPTION 'outbox retry policy update may only close one active recorded interval'
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER outbox_retry_policy_record_mutation_guard
BEFORE INSERT OR UPDATE OR DELETE ON public.outbox_retry_policy_record
FOR EACH ROW
EXECUTE FUNCTION public.protect_outbox_retry_policy_record();

CREATE FUNCTION public.reject_outbox_retry_policy_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'outbox retry policy records cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER outbox_retry_policy_record_truncate_guard
BEFORE TRUNCATE ON public.outbox_retry_policy_record
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_outbox_retry_policy_truncate();

CREATE FUNCTION public.calculate_outbox_retry_delay_seconds(
    p_delivery_attempt_count integer,
    p_base_delay_seconds integer,
    p_maximum_delay_seconds integer
)
RETURNS integer
LANGUAGE plpgsql
IMMUTABLE
STRICT
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    retry_delay_seconds integer;
    attempt_index integer;
BEGIN
    IF p_delivery_attempt_count < 1 OR p_delivery_attempt_count > 100 THEN
        RAISE EXCEPTION 'delivery attempt count must be between 1 and 100'
            USING ERRCODE = '22023';
    END IF;
    IF p_base_delay_seconds < 1
       OR p_base_delay_seconds > 86400
       OR p_maximum_delay_seconds < p_base_delay_seconds
       OR p_maximum_delay_seconds > 86400 THEN
        RAISE EXCEPTION 'retry policy delay bounds are invalid'
            USING ERRCODE = '22023';
    END IF;

    retry_delay_seconds := p_base_delay_seconds;
    IF p_delivery_attempt_count > 1 THEN
        FOR attempt_index IN 2..p_delivery_attempt_count LOOP
            IF retry_delay_seconds >= p_maximum_delay_seconds THEN
                EXIT;
            END IF;
            retry_delay_seconds := LEAST(
                p_maximum_delay_seconds,
                retry_delay_seconds * 2
            );
        END LOOP;
    END IF;
    RETURN retry_delay_seconds;
END;
$$;

CREATE FUNCTION public.enforce_outbox_retry_policy_transition()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    policy_base_delay_seconds integer;
    policy_maximum_delay_seconds integer;
    expected_retry_delay_seconds integer;
    expected_available_at timestamptz;
BEGIN
    IF OLD.delivery_state_code <> 'leased'
       OR NEW.delivery_state_code <> 'pending' THEN
        RETURN NEW;
    END IF;

    SELECT
        policy_record.base_delay_seconds,
        policy_record.maximum_delay_seconds
    INTO
        policy_base_delay_seconds,
        policy_maximum_delay_seconds
    FROM public.outbox_retry_policy_record AS policy_record
    WHERE policy_record.tenant_record_id = OLD.tenant_record_id
      AND policy_record.delivery_target_code = OLD.delivery_target_code
      AND policy_record.recorded_to IS NULL;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'active outbox retry policy not found'
            USING ERRCODE = '55000';
    END IF;

    expected_retry_delay_seconds := public.calculate_outbox_retry_delay_seconds(
        OLD.delivery_attempt_count,
        policy_base_delay_seconds,
        policy_maximum_delay_seconds
    );
    expected_available_at := GREATEST(
        OLD.available_at,
        transaction_timestamp()
            + pg_catalog.make_interval(secs => expected_retry_delay_seconds)
    );

    IF NEW.available_at IS DISTINCT FROM expected_available_at THEN
        RAISE EXCEPTION 'retry delay does not match active outbox retry policy'
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER outbox_delivery_retry_policy_guard
BEFORE UPDATE ON public.outbox_delivery_record
FOR EACH ROW
EXECUTE FUNCTION public.enforce_outbox_retry_policy_transition();

CREATE FUNCTION public.retry_outbox_delivery_with_policy(
    p_tenant_record_id uuid,
    p_outbox_delivery_record_id uuid,
    p_lease_owner_reference text,
    p_failure_code text
)
RETURNS TABLE (
    policy_version integer,
    retry_delay_seconds integer
)
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    current_delivery_target_code text;
    current_delivery_attempt_count integer;
    active_policy_version integer;
    active_base_delay_seconds integer;
    active_maximum_delay_seconds integer;
    selected_retry_delay_seconds integer;
BEGIN
    IF public.is_operational_uuid(p_tenant_record_id) IS NOT TRUE
       OR public.is_operational_uuid(p_outbox_delivery_record_id) IS NOT TRUE THEN
        RAISE EXCEPTION 'governed outbox retry identity uses a reserved UUID sentinel'
            USING ERRCODE = '23514';
    END IF;

    IF public.current_tenant_record_id() IS DISTINCT FROM p_tenant_record_id THEN
        RAISE EXCEPTION 'governed outbox retry tenant context does not match requested tenant'
            USING ERRCODE = '42501';
    END IF;

    SELECT
        delivery_record.delivery_target_code,
        delivery_record.delivery_attempt_count
    INTO
        current_delivery_target_code,
        current_delivery_attempt_count
    FROM public.outbox_delivery_record AS delivery_record
    WHERE delivery_record.tenant_record_id = p_tenant_record_id
      AND delivery_record.outbox_delivery_record_id = p_outbox_delivery_record_id
    FOR UPDATE OF delivery_record;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'outbox delivery record not found'
            USING ERRCODE = 'P0002';
    END IF;

    SELECT
        policy_record.policy_version,
        policy_record.base_delay_seconds,
        policy_record.maximum_delay_seconds
    INTO
        active_policy_version,
        active_base_delay_seconds,
        active_maximum_delay_seconds
    FROM public.outbox_retry_policy_record AS policy_record
    WHERE policy_record.tenant_record_id = p_tenant_record_id
      AND policy_record.delivery_target_code = current_delivery_target_code
      AND policy_record.recorded_to IS NULL;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'active outbox retry policy not found'
            USING ERRCODE = '55000';
    END IF;

    selected_retry_delay_seconds := public.calculate_outbox_retry_delay_seconds(
        current_delivery_attempt_count,
        active_base_delay_seconds,
        active_maximum_delay_seconds
    );

    PERFORM public.retry_outbox_delivery(
        p_tenant_record_id,
        p_outbox_delivery_record_id,
        p_lease_owner_reference,
        p_failure_code,
        selected_retry_delay_seconds
    );

    policy_version := active_policy_version;
    retry_delay_seconds := selected_retry_delay_seconds;
    RETURN NEXT;
END;
$$;
