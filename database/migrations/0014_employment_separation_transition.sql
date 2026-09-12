-- Add the authoritative bitemporal Employment separation transition.
--
-- Separation is a correction-not-rewrite operation on one Employment aggregate.
-- The current recorded version is closed at a database-owned time, the surviving
-- pre-separation business interval is re-recorded when non-empty, and a terminal
-- version begins on the effective separation date. Assignment history is never
-- rewritten here: any Assignment that would remain effective on/after separation
-- causes the command to fail closed so the Assignment owner can coordinate first.

BEGIN;

SET LOCAL search_path = public, pg_catalog;

ALTER TABLE public.people_mutation_idempotency_record
    DROP CONSTRAINT people_mutation_idempotency_route_check;
ALTER TABLE public.people_mutation_idempotency_record
    ADD CONSTRAINT people_mutation_idempotency_route_check
    CHECK (
        command_route IN (
            'candidate-worker-conversions',
            'employment-records',
            'employment-separations',
            'position-records',
            'assignment-records'
        )
    );

ALTER TABLE public.employment_record_version
    ADD CONSTRAINT employment_record_version_tenant_identity_unique
    UNIQUE (tenant_record_id, employment_record_version_id);

CREATE TABLE public.employment_separation_record (
    tenant_record_id uuid NOT NULL REFERENCES public.tenant_record(tenant_record_id),
    employment_separation_record_id uuid PRIMARY KEY,
    employment_record_id uuid NOT NULL,
    person_record_id uuid NOT NULL,
    prior_employment_record_version_id uuid NOT NULL,
    continuation_employment_record_version_id uuid,
    separated_employment_record_version_id uuid NOT NULL,
    separation_effective_on date NOT NULL,
    separation_status_code text NOT NULL,
    separation_reason_code text NOT NULL,
    evidence_reference text NOT NULL,
    evidence_version_code text NOT NULL,
    actor_reference text NOT NULL,
    purpose_code text NOT NULL,
    confirmation_reference text NOT NULL,
    command_digest text NOT NULL,
    audit_event_record_id uuid NOT NULL,
    recorded_at timestamptz NOT NULL,
    CONSTRAINT employment_separation_record_id_operational_check
        CHECK (public.is_operational_uuid(employment_separation_record_id)),
    CONSTRAINT employment_separation_prior_version_operational_check
        CHECK (public.is_operational_uuid(prior_employment_record_version_id)),
    CONSTRAINT employment_separation_continuation_version_operational_check
        CHECK (
            continuation_employment_record_version_id IS NULL
            OR public.is_operational_uuid(continuation_employment_record_version_id)
        ),
    CONSTRAINT employment_separation_terminal_version_operational_check
        CHECK (public.is_operational_uuid(separated_employment_record_version_id)),
    CONSTRAINT employment_separation_employment_person_tenant_fk
        FOREIGN KEY (tenant_record_id, employment_record_id, person_record_id)
        REFERENCES public.employment_record(
            tenant_record_id,
            employment_record_id,
            person_record_id
        ),
    CONSTRAINT employment_separation_prior_version_tenant_fk
        FOREIGN KEY (tenant_record_id, prior_employment_record_version_id)
        REFERENCES public.employment_record_version(
            tenant_record_id,
            employment_record_version_id
        ),
    CONSTRAINT employment_separation_continuation_version_tenant_fk
        FOREIGN KEY (tenant_record_id, continuation_employment_record_version_id)
        REFERENCES public.employment_record_version(
            tenant_record_id,
            employment_record_version_id
        ),
    CONSTRAINT employment_separation_terminal_version_tenant_fk
        FOREIGN KEY (tenant_record_id, separated_employment_record_version_id)
        REFERENCES public.employment_record_version(
            tenant_record_id,
            employment_record_version_id
        ),
    CONSTRAINT employment_separation_audit_event_tenant_fk
        FOREIGN KEY (tenant_record_id, audit_event_record_id)
        REFERENCES public.audit_event_record(tenant_record_id, audit_event_record_id),
    CONSTRAINT employment_separation_status_check
        CHECK (separation_status_code = 'terminated'),
    CONSTRAINT employment_separation_reason_check
        CHECK (separation_reason_code ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'),
    CONSTRAINT employment_separation_evidence_reference_check
        CHECK (evidence_reference ~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$'),
    CONSTRAINT employment_separation_evidence_version_check
        CHECK (evidence_version_code ~ '^[A-Za-z0-9][A-Za-z0-9._:-]*$'),
    CONSTRAINT employment_separation_actor_reference_check
        CHECK (actor_reference ~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$'),
    CONSTRAINT employment_separation_purpose_check
        CHECK (purpose_code = 'workforce_admin'),
    CONSTRAINT employment_separation_confirmation_reference_check
        CHECK (confirmation_reference ~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$'),
    CONSTRAINT employment_separation_command_digest_check
        CHECK (command_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT employment_separation_tenant_identity_unique
        UNIQUE (tenant_record_id, employment_separation_record_id),
    CONSTRAINT employment_separation_terminal_version_unique
        UNIQUE (tenant_record_id, separated_employment_record_version_id),
    CONSTRAINT employment_separation_audit_event_unique
        UNIQUE (tenant_record_id, audit_event_record_id)
);

CREATE TRIGGER employment_separation_append_only_guard
BEFORE UPDATE OR DELETE ON public.employment_separation_record
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

CREATE FUNCTION public.reject_employment_separation_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'employment separation records cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER employment_separation_truncate_guard
BEFORE TRUNCATE ON public.employment_separation_record
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_employment_separation_truncate();

REVOKE TRUNCATE ON public.employment_separation_record FROM PUBLIC;

ALTER TABLE public.employment_separation_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.employment_separation_record FORCE ROW LEVEL SECURITY;
CREATE POLICY employment_separation_scope_policy ON public.employment_separation_record
USING (tenant_record_id = public.current_tenant_record_id())
WITH CHECK (tenant_record_id = public.current_tenant_record_id());

CREATE FUNCTION public.separate_employment_record_once(
    p_tenant_record_id uuid,
    p_person_record_id uuid,
    p_employment_record_id uuid,
    p_expected_employment_record_version_id uuid,
    p_separation_effective_on date,
    p_separation_reason_code text,
    p_evidence_reference text,
    p_evidence_version_code text,
    p_actor_reference text,
    p_purpose_code text,
    p_confirmation_reference text,
    p_idempotency_key text,
    p_audit_event_record_id uuid,
    p_outbox_delivery_record_id uuid
)
RETURNS TABLE (
    employment_record_id uuid,
    separated_employment_record_version_id uuid,
    recorded_at timestamptz,
    replayed boolean
)
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    v_route constant text := 'employment-separations';
    v_current_tenant uuid;
    v_command_digest text;
    v_replay_record_id uuid;
    v_replay_digest text;
    v_anchor_person_id uuid;
    v_current_status text;
    v_current_concurrency text;
    v_current_effective_from date;
    v_current_effective_to date;
    v_recorded_at timestamptz;
    v_continuation_version_id uuid;
    v_separated_version_id uuid;
    v_separation_record_id uuid;
    v_idempotency_record_id uuid;
    v_event_time text;
    v_canonical_event_json text;
    v_event_envelope_digest text;
BEGIN
    v_current_tenant := public.current_tenant_record_id();
    IF v_current_tenant IS DISTINCT FROM p_tenant_record_id THEN
        RAISE EXCEPTION 'employment separation tenant context does not match command tenant'
            USING ERRCODE = '42501';
    END IF;

    IF public.is_operational_uuid(p_tenant_record_id) IS NOT TRUE
       OR public.is_operational_uuid(p_person_record_id) IS NOT TRUE
       OR public.is_operational_uuid(p_employment_record_id) IS NOT TRUE
       OR public.is_operational_uuid(p_expected_employment_record_version_id) IS NOT TRUE
       OR public.is_operational_uuid(p_audit_event_record_id) IS NOT TRUE
       OR public.is_operational_uuid(p_outbox_delivery_record_id) IS NOT TRUE THEN
        RAISE EXCEPTION 'employment separation identities must be operational UUIDs'
            USING ERRCODE = '22023';
    END IF;
    IF p_separation_effective_on IS NULL THEN
        RAISE EXCEPTION 'employment separation effective date is required'
            USING ERRCODE = '22023';
    END IF;
    IF p_separation_reason_code IS NULL
       OR p_separation_reason_code !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$' THEN
        RAISE EXCEPTION 'employment separation reason code is invalid'
            USING ERRCODE = '22023';
    END IF;
    IF p_evidence_reference IS NULL
       OR p_evidence_reference !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$' THEN
        RAISE EXCEPTION 'employment separation evidence reference is invalid'
            USING ERRCODE = '22023';
    END IF;
    IF p_evidence_version_code IS NULL
       OR p_evidence_version_code !~ '^[A-Za-z0-9][A-Za-z0-9._:-]*$' THEN
        RAISE EXCEPTION 'employment separation evidence version is invalid'
            USING ERRCODE = '22023';
    END IF;
    IF p_actor_reference IS NULL
       OR p_actor_reference !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$' THEN
        RAISE EXCEPTION 'employment separation actor reference is invalid'
            USING ERRCODE = '22023';
    END IF;
    IF p_purpose_code IS DISTINCT FROM 'workforce_admin' THEN
        RAISE EXCEPTION 'employment separation requires workforce_admin purpose'
            USING ERRCODE = '42501';
    END IF;
    IF p_confirmation_reference IS NULL
       OR p_confirmation_reference !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$' THEN
        RAISE EXCEPTION 'employment separation confirmation reference is invalid'
            USING ERRCODE = '22023';
    END IF;
    IF p_idempotency_key IS NULL
       OR char_length(p_idempotency_key) NOT BETWEEN 16 AND 200
       OR p_idempotency_key !~ '^[\x21-\x7E]+$' THEN
        RAISE EXCEPTION 'employment separation idempotency key is invalid'
            USING ERRCODE = '22023';
    END IF;

    v_command_digest := encode(
        digest(
            convert_to(
                jsonb_build_object(
                    'actor_reference', p_actor_reference,
                    'command_route', v_route,
                    'confirmation_reference', p_confirmation_reference,
                    'employment_record_id', p_employment_record_id::text,
                    'evidence_reference', p_evidence_reference,
                    'evidence_version_code', p_evidence_version_code,
                    'expected_employment_record_version_id', p_expected_employment_record_version_id::text,
                    'person_record_id', p_person_record_id::text,
                    'purpose_code', p_purpose_code,
                    'separation_effective_on', p_separation_effective_on::text,
                    'separation_reason_code', p_separation_reason_code,
                    'separation_status_code', 'terminated',
                    'tenant_record_id', p_tenant_record_id::text
                )::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(
            p_tenant_record_id::text || E'\x1f' || v_route || E'\x1f' || p_idempotency_key,
            0
        )
    );

    SELECT replay.created_record_id, replay.command_digest
    INTO v_replay_record_id, v_replay_digest
    FROM public.people_mutation_idempotency_record AS replay
    WHERE replay.tenant_record_id = p_tenant_record_id
      AND replay.command_route = v_route
      AND replay.idempotency_key = p_idempotency_key;

    IF FOUND THEN
        IF v_replay_digest IS DISTINCT FROM v_command_digest THEN
            RAISE EXCEPTION 'employment separation idempotency key is bound to a different command'
                USING ERRCODE = '23505';
        END IF;
        RETURN QUERY
        SELECT
            separation.employment_record_id,
            separation.separated_employment_record_version_id,
            separation.recorded_at,
            true
        FROM public.employment_separation_record AS separation
        WHERE separation.tenant_record_id = p_tenant_record_id
          AND separation.separated_employment_record_version_id = v_replay_record_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'employment separation replay evidence is missing'
                USING ERRCODE = '55000';
        END IF;
        RETURN;
    END IF;

    SELECT employment.person_record_id
    INTO v_anchor_person_id
    FROM public.employment_record AS employment
    WHERE employment.tenant_record_id = p_tenant_record_id
      AND employment.employment_record_id = p_employment_record_id
    FOR UPDATE OF employment;
    IF NOT FOUND OR v_anchor_person_id IS DISTINCT FROM p_person_record_id THEN
        RAISE EXCEPTION 'employment separation target does not match tenant person and employment'
            USING ERRCODE = '23503';
    END IF;

    SELECT
        version.employment_status_code,
        version.employment_concurrency_code,
        version.effective_from,
        version.effective_to
    INTO
        v_current_status,
        v_current_concurrency,
        v_current_effective_from,
        v_current_effective_to
    FROM public.employment_record_version AS version
    WHERE version.tenant_record_id = p_tenant_record_id
      AND version.employment_record_id = p_employment_record_id
      AND version.employment_record_version_id = p_expected_employment_record_version_id
      AND version.recorded_to IS NULL
    FOR UPDATE OF version;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'employment separation expected version is stale or unavailable'
            USING ERRCODE = '40001';
    END IF;
    IF v_current_status NOT IN ('active', 'leave') THEN
        RAISE EXCEPTION 'employment separation requires an active or leave employment version'
            USING ERRCODE = '55000';
    END IF;
    IF p_separation_effective_on < v_current_effective_from
       OR (v_current_effective_to IS NOT NULL AND p_separation_effective_on >= v_current_effective_to) THEN
        RAISE EXCEPTION 'employment separation date is outside the expected current business interval'
            USING ERRCODE = '22023';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.employment_record_version AS other_version
        WHERE other_version.tenant_record_id = p_tenant_record_id
          AND other_version.employment_record_id = p_employment_record_id
          AND other_version.employment_record_version_id <> p_expected_employment_record_version_id
          AND other_version.recorded_to IS NULL
          AND daterange(other_version.effective_from, other_version.effective_to, '[)')
              && daterange(p_separation_effective_on, NULL, '[)')
    ) THEN
        RAISE EXCEPTION 'employment separation requires future Employment version coordination'
            USING ERRCODE = '55000';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.assignment_record AS assignment
        WHERE assignment.tenant_record_id = p_tenant_record_id
          AND assignment.employment_record_id = p_employment_record_id
          AND assignment.recorded_to IS NULL
          AND (assignment.effective_to IS NULL OR assignment.effective_to > p_separation_effective_on)
    ) THEN
        RAISE EXCEPTION 'employment separation requires assignment coordination before termination'
            USING ERRCODE = '55000';
    END IF;

    v_recorded_at := pg_catalog.clock_timestamp();
    v_separated_version_id := gen_random_uuid();
    v_separation_record_id := gen_random_uuid();
    v_idempotency_record_id := gen_random_uuid();

    UPDATE public.employment_record_version
    SET recorded_to = v_recorded_at
    WHERE tenant_record_id = p_tenant_record_id
      AND employment_record_version_id = p_expected_employment_record_version_id
      AND recorded_to IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'employment separation expected version changed during transition'
            USING ERRCODE = '40001';
    END IF;

    IF p_separation_effective_on > v_current_effective_from THEN
        v_continuation_version_id := gen_random_uuid();
        INSERT INTO public.employment_record_version (
            tenant_record_id,
            employment_record_version_id,
            employment_record_id,
            employment_status_code,
            employment_concurrency_code,
            effective_from,
            effective_to,
            recorded_from
        ) VALUES (
            p_tenant_record_id,
            v_continuation_version_id,
            p_employment_record_id,
            v_current_status,
            v_current_concurrency,
            v_current_effective_from,
            p_separation_effective_on,
            v_recorded_at
        );
    END IF;

    INSERT INTO public.employment_record_version (
        tenant_record_id,
        employment_record_version_id,
        employment_record_id,
        employment_status_code,
        employment_concurrency_code,
        effective_from,
        effective_to,
        recorded_from
    ) VALUES (
        p_tenant_record_id,
        v_separated_version_id,
        p_employment_record_id,
        'terminated',
        v_current_concurrency,
        p_separation_effective_on,
        NULL,
        v_recorded_at
    );

    v_event_time := pg_catalog.to_char(
        v_recorded_at AT TIME ZONE 'UTC',
        'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'
    );
    v_canonical_event_json :=
        '{"data":{"high_impact":true,"result_code":"employment_separated"},'
        || '"datacontenttype":"application/json",'
        || '"id":' || pg_catalog.to_json(p_audit_event_record_id::text)::text || ','
        || '"orgmetraactor":' || pg_catalog.to_json(p_actor_reference)::text || ','
        || '"orgmetraconfirmation":' || pg_catalog.to_json(p_confirmation_reference)::text || ','
        || '"orgmetraevidence":' || pg_catalog.to_json(p_evidence_version_code)::text || ','
        || '"orgmetrapurpose":' || pg_catalog.to_json(p_purpose_code)::text || ','
        || '"orgmetrareason":' || pg_catalog.to_json(p_separation_reason_code)::text || ','
        || '"orgmetratenant":' || pg_catalog.to_json(p_tenant_record_id::text)::text || ','
        || '"source":"urn:orgmetra:people_api",'
        || '"specversion":"1.0",'
        || '"subject":' || pg_catalog.to_json('employment_record:' || p_employment_record_id::text)::text || ','
        || '"time":' || pg_catalog.to_json(v_event_time)::text || ','
        || '"type":"orgmetra.people.employment_separated"}';
    v_event_envelope_digest := encode(
        digest(convert_to(v_canonical_event_json, 'UTF8'), 'sha256'),
        'hex'
    );

    PERFORM public.record_audit_outbox_event(
        p_tenant_record_id,
        p_audit_event_record_id,
        p_outbox_delivery_record_id,
        v_canonical_event_json,
        v_event_envelope_digest,
        'orgmetra_domain_events'
    );

    INSERT INTO public.employment_separation_record (
        tenant_record_id,
        employment_separation_record_id,
        employment_record_id,
        person_record_id,
        prior_employment_record_version_id,
        continuation_employment_record_version_id,
        separated_employment_record_version_id,
        separation_effective_on,
        separation_status_code,
        separation_reason_code,
        evidence_reference,
        evidence_version_code,
        actor_reference,
        purpose_code,
        confirmation_reference,
        command_digest,
        audit_event_record_id,
        recorded_at
    ) VALUES (
        p_tenant_record_id,
        v_separation_record_id,
        p_employment_record_id,
        p_person_record_id,
        p_expected_employment_record_version_id,
        v_continuation_version_id,
        v_separated_version_id,
        p_separation_effective_on,
        'terminated',
        p_separation_reason_code,
        p_evidence_reference,
        p_evidence_version_code,
        p_actor_reference,
        p_purpose_code,
        p_confirmation_reference,
        v_command_digest,
        p_audit_event_record_id,
        v_recorded_at
    );

    INSERT INTO public.people_mutation_idempotency_record (
        tenant_record_id,
        people_mutation_idempotency_record_id,
        command_route,
        idempotency_key,
        command_digest,
        created_record_id,
        recorded_from
    ) VALUES (
        p_tenant_record_id,
        v_idempotency_record_id,
        v_route,
        p_idempotency_key,
        v_command_digest,
        v_separated_version_id,
        v_recorded_at
    );

    RETURN QUERY SELECT p_employment_record_id, v_separated_version_id, v_recorded_at, false;
END;
$$;

COMMIT;
