-- Close review-identified durability and name-resolution gaps without weakening
-- the existing outbox state machine. This migration intentionally hardens the
-- already-published 0003-0007 contracts instead of bypassing them.

-- Recovery-role names are security boundaries. Reusing an existing cluster
-- role could retain memberships or object ACLs that ALTER ROLE does not erase.
-- Fail before changing any project object so a collision cannot leave partial
-- migration state behind.
DO $orgmetra_role_preflight$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_catalog.pg_roles
        WHERE rolname IN (
            'orgmetra_outbox_recovery_owner',
            'orgmetra_outbox_operator'
        )
    ) THEN
        RAISE EXCEPTION 'pre-existing outbox recovery role is not accepted'
            USING ERRCODE = '42710';
    END IF;
END;
$orgmetra_role_preflight$;

-- Everything before the online index build is atomic. The index itself must be
-- outside an explicit transaction because PostgreSQL forbids CONCURRENTLY in a
-- transaction block.
BEGIN;

-- Project objects currently live in public. Make that schema trusted before
-- pinning function search paths so caller-controlled schemas cannot shadow
-- tenant helpers, tables, or pgcrypto functions.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

CREATE OR REPLACE FUNCTION public.validate_audit_event_envelope(
    p_canonical_event_json text,
    p_audit_event_record_id uuid,
    p_tenant_record_id uuid,
    p_event_envelope_digest text
)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
STRICT
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    event_envelope jsonb;
    event_data jsonb;
    event_keys text[];
    data_keys text[];
    event_high_impact boolean;
    event_time_text text;
    event_year integer;
    event_month integer;
    event_day integer;
    event_hour integer;
    event_minute integer;
    event_second integer;
    expected_keys_without_confirmation constant text[] := ARRAY[
        'data',
        'datacontenttype',
        'id',
        'orgmetraactor',
        'orgmetraevidence',
        'orgmetrapurpose',
        'orgmetrareason',
        'orgmetratenant',
        'source',
        'specversion',
        'subject',
        'time',
        'type'
    ];
    expected_keys_with_confirmation constant text[] := ARRAY[
        'data',
        'datacontenttype',
        'id',
        'orgmetraactor',
        'orgmetraconfirmation',
        'orgmetraevidence',
        'orgmetrapurpose',
        'orgmetrareason',
        'orgmetratenant',
        'source',
        'specversion',
        'subject',
        'time',
        'type'
    ];
BEGIN
    IF public.is_operational_uuid(p_audit_event_record_id) IS NOT TRUE
       OR public.is_operational_uuid(p_tenant_record_id) IS NOT TRUE THEN
        RETURN false;
    END IF;

    BEGIN
        event_envelope := p_canonical_event_json::jsonb;
    EXCEPTION
        WHEN others THEN
            RETURN false;
    END;

    IF pg_catalog.jsonb_typeof(event_envelope) <> 'object' THEN
        RETURN false;
    END IF;

    SELECT pg_catalog.array_agg(event_key ORDER BY event_key COLLATE "C")
    INTO event_keys
    FROM pg_catalog.jsonb_object_keys(event_envelope) AS event_key_set(event_key);

    IF event_keys IS NULL
       OR (
           event_keys IS DISTINCT FROM expected_keys_without_confirmation
           AND event_keys IS DISTINCT FROM expected_keys_with_confirmation
       ) THEN
        RETURN false;
    END IF;

    event_data := event_envelope -> 'data';
    IF pg_catalog.jsonb_typeof(event_data) <> 'object' THEN
        RETURN false;
    END IF;

    SELECT pg_catalog.array_agg(data_key ORDER BY data_key COLLATE "C")
    INTO data_keys
    FROM pg_catalog.jsonb_object_keys(event_data) AS data_key_set(data_key);
    IF data_keys IS DISTINCT FROM ARRAY['high_impact', 'result_code']::text[] THEN
        RETURN false;
    END IF;

    IF event_envelope ->> 'specversion' <> '1.0'
       OR event_envelope ->> 'datacontenttype' <> 'application/json'
       OR event_envelope ->> 'id' <> p_audit_event_record_id::text
       OR event_envelope ->> 'orgmetratenant' <> p_tenant_record_id::text THEN
        RETURN false;
    END IF;

    IF pg_catalog.jsonb_typeof(event_envelope -> 'id') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'source') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'type') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'subject') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'time') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'orgmetraactor') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'orgmetrapurpose') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'orgmetrareason') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'orgmetraevidence') <> 'string'
       OR pg_catalog.jsonb_typeof(event_data -> 'result_code') <> 'string'
       OR pg_catalog.jsonb_typeof(event_data -> 'high_impact') <> 'boolean' THEN
        RETURN false;
    END IF;

    IF (event_envelope ->> 'source') COLLATE "C"
            !~ '^urn:orgmetra:[a-z][a-z0-9]*(?:_[a-z0-9]+)+$'
       OR (event_envelope ->> 'type') COLLATE "C"
            !~ '^orgmetra(?:\.[a-z][a-z0-9_]*){2,}$'
       OR (event_envelope ->> 'subject') COLLATE "C"
            !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$'
       OR (event_envelope ->> 'orgmetraactor') COLLATE "C"
            !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$'
       OR (event_envelope ->> 'orgmetrapurpose') COLLATE "C"
            !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
       OR (event_envelope ->> 'orgmetrareason') COLLATE "C"
            !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
       OR (event_envelope ->> 'orgmetraevidence') COLLATE "C"
            !~ '^[A-Za-z0-9][A-Za-z0-9._:-]*$'
       OR (event_data ->> 'result_code') COLLATE "C"
            !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$' THEN
        RETURN false;
    END IF;

    event_time_text := event_envelope ->> 'time';
    IF event_time_text COLLATE "C"
            !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$' THEN
        RETURN false;
    END IF;

    BEGIN
        event_year := pg_catalog.substr(event_time_text, 1, 4)::integer;
        event_month := pg_catalog.substr(event_time_text, 6, 2)::integer;
        event_day := pg_catalog.substr(event_time_text, 9, 2)::integer;
        event_hour := pg_catalog.substr(event_time_text, 12, 2)::integer;
        event_minute := pg_catalog.substr(event_time_text, 15, 2)::integer;
        event_second := pg_catalog.substr(event_time_text, 18, 2)::integer;
        PERFORM pg_catalog.make_date(event_year, event_month, event_day);
    EXCEPTION
        WHEN others THEN
            RETURN false;
    END;

    IF event_hour > 23 OR event_minute > 59 OR event_second > 59 THEN
        RETURN false;
    END IF;

    event_high_impact := (event_data ->> 'high_impact')::boolean;
    IF event_high_impact THEN
        IF NOT (event_envelope ? 'orgmetraconfirmation')
           OR pg_catalog.jsonb_typeof(event_envelope -> 'orgmetraconfirmation') <> 'string'
           OR (event_envelope ->> 'orgmetraconfirmation') COLLATE "C"
              !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$' THEN
            RETURN false;
        END IF;
    ELSIF event_envelope ? 'orgmetraconfirmation' THEN
        IF pg_catalog.jsonb_typeof(event_envelope -> 'orgmetraconfirmation') <> 'string'
           OR (event_envelope ->> 'orgmetraconfirmation') COLLATE "C"
              !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$' THEN
            RETURN false;
        END IF;
    END IF;

    IF p_event_envelope_digest COLLATE "C" !~ '^[0-9a-f]{64}$'
       OR pg_catalog.encode(
            public.digest(pg_catalog.convert_to(p_canonical_event_json, 'UTF8'), 'sha256'),
            'hex'
          ) <> p_event_envelope_digest THEN
        RETURN false;
    END IF;

    RETURN true;
END;
$$;

-- Existing boundary bodies continue to own their business rules, but their
-- object resolution is made deterministic and caller-independent.
ALTER FUNCTION public.record_audit_outbox_event(uuid, uuid, uuid, text, text, text)
    SET search_path = pg_catalog, public, pg_temp;
ALTER FUNCTION public.protect_outbox_delivery_transition()
    SET search_path = pg_catalog, public, pg_temp;
ALTER FUNCTION public.claim_outbox_delivery(uuid, text, text, integer)
    SET search_path = pg_catalog, public, pg_temp;
ALTER FUNCTION public.complete_outbox_delivery(uuid, uuid, text)
    SET search_path = pg_catalog, public, pg_temp;
ALTER FUNCTION public.retry_outbox_delivery(uuid, uuid, text, text, integer)
    SET search_path = pg_catalog, public, pg_temp;
ALTER FUNCTION public.dead_letter_outbox_delivery(uuid, uuid, uuid, text, text, text)
    SET search_path = pg_catalog, public, pg_temp;
ALTER FUNCTION public.reject_audit_event_mutation()
    SET search_path = pg_catalog, public, pg_temp;

-- Row triggers do not see TRUNCATE. Add explicit statement-level guards so
-- immutable audit evidence and governed delivery state cannot be bulk-erased.
CREATE TRIGGER audit_event_record_truncate_guard
BEFORE TRUNCATE ON public.audit_event_record
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_audit_event_mutation();

CREATE FUNCTION public.reject_outbox_delivery_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'outbox delivery records cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER outbox_delivery_record_truncate_guard
BEFORE TRUNCATE ON public.outbox_delivery_record
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_outbox_delivery_truncate();

-- PostgreSQL does not grant TRUNCATE to PUBLIC by default. Keep the explicit
-- revoke as defense-in-depth documentation of the immutable-history boundary.
REVOKE TRUNCATE ON public.audit_event_record, public.outbox_delivery_record FROM PUBLIC;

COMMIT;

-- Claim scans are latency-sensitive and accumulate with durable audit history.
-- Established deployments build this index without blocking queue writers.
CREATE INDEX CONCURRENTLY outbox_delivery_due_work_index
    ON public.outbox_delivery_record (
        tenant_record_id,
        available_at,
        outbox_delivery_record_id
    )
    WHERE delivery_state_code IN ('pending', 'leased');

-- Role creation, privilege grants, temporary schema CREATE, ownership transfer,
-- SECURITY DEFINER elevation, cleanup, and final EXECUTE grant are one atomic
-- unit. An interruption cannot strand the temporary schema-creation privilege.
BEGIN;

-- When the final-attempt worker disappears permanently, only an explicit
-- operator path may terminate the expired lease. It records immutable
-- escalation evidence before the existing transition trigger permits the
-- dead-letter state change. Public callers do not receive this capability.
CREATE FUNCTION public.operator_dead_letter_expired_outbox_delivery(
    p_tenant_record_id uuid,
    p_outbox_delivery_record_id uuid,
    p_outbox_delivery_escalation_record_id uuid,
    p_operator_reference text,
    p_failure_code text
)
RETURNS void
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    current_state_code text;
    current_attempt_count integer;
    current_maximum_attempt_count integer;
    current_lease_expires_at timestamptz;
BEGIN
    IF public.is_operational_uuid(p_tenant_record_id) IS NOT TRUE
       OR public.is_operational_uuid(p_outbox_delivery_record_id) IS NOT TRUE
       OR public.is_operational_uuid(p_outbox_delivery_escalation_record_id) IS NOT TRUE THEN
        RAISE EXCEPTION 'operator dead-letter identity uses a reserved UUID sentinel'
            USING ERRCODE = '23514';
    END IF;

    IF public.current_tenant_record_id() IS DISTINCT FROM p_tenant_record_id THEN
        RAISE EXCEPTION 'operator dead-letter tenant context does not match requested tenant'
            USING ERRCODE = '42501';
    END IF;

    IF p_operator_reference IS NULL
       OR p_operator_reference COLLATE "C"
          !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$' THEN
        RAISE EXCEPTION 'operator reference must be a namespaced opaque reference'
            USING ERRCODE = '22023';
    END IF;

    IF p_failure_code IS NULL
       OR p_failure_code COLLATE "C"
          !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$' THEN
        RAISE EXCEPTION 'failure code must be a lower snake_case code'
            USING ERRCODE = '22023';
    END IF;

    SELECT
        delivery_record.delivery_state_code,
        delivery_record.delivery_attempt_count,
        delivery_record.maximum_attempt_count,
        delivery_record.lease_expires_at
    INTO
        current_state_code,
        current_attempt_count,
        current_maximum_attempt_count,
        current_lease_expires_at
    FROM public.outbox_delivery_record AS delivery_record
    WHERE delivery_record.tenant_record_id = p_tenant_record_id
      AND delivery_record.outbox_delivery_record_id = p_outbox_delivery_record_id
    FOR UPDATE OF delivery_record;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'outbox delivery record not found'
            USING ERRCODE = 'P0002';
    END IF;

    IF current_state_code <> 'leased' THEN
        RAISE EXCEPTION 'operator recovery requires a leased delivery'
            USING ERRCODE = '55000';
    END IF;

    IF current_attempt_count < current_maximum_attempt_count THEN
        RAISE EXCEPTION 'operator recovery requires exhausted stored attempt budget'
            USING ERRCODE = '55000';
    END IF;

    IF current_lease_expires_at IS NULL
       OR current_lease_expires_at > pg_catalog.transaction_timestamp() THEN
        RAISE EXCEPTION 'operator recovery requires an expired final lease'
            USING ERRCODE = '55000';
    END IF;

    INSERT INTO public.outbox_delivery_escalation_record (
        tenant_record_id,
        outbox_delivery_escalation_record_id,
        outbox_delivery_record_id,
        failure_code,
        escalation_reference,
        terminal_attempt_count
    ) VALUES (
        p_tenant_record_id,
        p_outbox_delivery_escalation_record_id,
        p_outbox_delivery_record_id,
        p_failure_code,
        p_operator_reference,
        current_attempt_count
    );

    UPDATE public.outbox_delivery_record AS delivery_record
    SET delivery_state_code = 'dead_lettered',
        lease_owner_reference = NULL,
        lease_expires_at = NULL,
        last_failure_code = p_failure_code
    WHERE delivery_record.tenant_record_id = p_tenant_record_id
      AND delivery_record.outbox_delivery_record_id = p_outbox_delivery_record_id;

    -- The escalation-binding constraint trigger is initially deferred. Force
    -- this function's pending evidence check while SECURITY DEFINER privileges
    -- are still active, then restore the transaction's deferred mode so the
    -- caller does not need direct SELECT privileges on transport tables.
    SET CONSTRAINTS public.outbox_delivery_escalation_binding_guard IMMEDIATE;
    SET CONSTRAINTS public.outbox_delivery_escalation_binding_guard DEFERRED;
END;
$$;

-- Default function EXECUTE is granted to PUBLIC by PostgreSQL, so revoke it
-- before elevating the operator recovery boundary to SECURITY DEFINER.
REVOKE ALL ON FUNCTION public.operator_dead_letter_expired_outbox_delivery(
    uuid, uuid, uuid, text, text
) FROM PUBLIC;

-- Separate the externally assignable operator capability from the non-login
-- function owner. Any pre-existing role name was rejected before project DDL,
-- so these fresh roles cannot inherit undisclosed memberships or object ACLs.
CREATE ROLE orgmetra_outbox_recovery_owner
    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE orgmetra_outbox_operator
    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

GRANT USAGE ON SCHEMA public TO orgmetra_outbox_recovery_owner, orgmetra_outbox_operator;
GRANT SELECT ON public.outbox_delivery_record TO orgmetra_outbox_recovery_owner;
GRANT UPDATE (
    delivery_state_code,
    lease_owner_reference,
    lease_expires_at,
    last_failure_code
) ON public.outbox_delivery_record TO orgmetra_outbox_recovery_owner;
GRANT SELECT, INSERT ON public.outbox_delivery_escalation_record
    TO orgmetra_outbox_recovery_owner;
GRANT EXECUTE ON FUNCTION public.is_operational_uuid(uuid)
    TO orgmetra_outbox_recovery_owner;
GRANT EXECUTE ON FUNCTION public.current_tenant_record_id()
    TO orgmetra_outbox_recovery_owner;
GRANT EXECUTE ON FUNCTION public.protect_outbox_delivery_transition()
    TO orgmetra_outbox_recovery_owner;
GRANT EXECUTE ON FUNCTION public.validate_outbox_delivery_escalation_binding()
    TO orgmetra_outbox_recovery_owner;

-- ALTER FUNCTION OWNER requires CREATE on the containing schema for the target
-- owner. Grant it only inside this transaction for the ownership handoff, then
-- revoke it before the transaction can commit.
GRANT CREATE ON SCHEMA public TO orgmetra_outbox_recovery_owner;
ALTER FUNCTION public.operator_dead_letter_expired_outbox_delivery(
    uuid, uuid, uuid, text, text
) OWNER TO orgmetra_outbox_recovery_owner;
ALTER FUNCTION public.operator_dead_letter_expired_outbox_delivery(
    uuid, uuid, uuid, text, text
) SECURITY DEFINER;
REVOKE CREATE ON SCHEMA public FROM orgmetra_outbox_recovery_owner;
GRANT EXECUTE ON FUNCTION public.operator_dead_letter_expired_outbox_delivery(
    uuid, uuid, uuid, text, text
) TO orgmetra_outbox_operator;

COMMIT;
