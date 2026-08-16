-- Persist governed audit evidence and asynchronous delivery state without
-- allowing the mutable outbox lifecycle to rewrite immutable audit history.
-- The caller supplies AuditOutboxEvent.canonical_json() and content_digest()
-- inside the same transaction as the owning business mutation.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE FUNCTION validate_audit_event_envelope(
    p_canonical_event_json text,
    p_audit_event_record_id uuid,
    p_tenant_record_id uuid,
    p_event_envelope_digest text
)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
DECLARE
    event_envelope jsonb;
    event_data jsonb;
    event_keys text[];
    data_keys text[];
    event_high_impact boolean;
    event_time timestamptz;
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
    IF is_operational_uuid(p_audit_event_record_id) IS NOT TRUE
       OR is_operational_uuid(p_tenant_record_id) IS NOT TRUE THEN
        RETURN false;
    END IF;

    BEGIN
        event_envelope := p_canonical_event_json::jsonb;
    EXCEPTION
        WHEN others THEN
            RETURN false;
    END;

    IF jsonb_typeof(event_envelope) <> 'object' THEN
        RETURN false;
    END IF;

    SELECT array_agg(event_key ORDER BY event_key)
    INTO event_keys
    FROM jsonb_object_keys(event_envelope) AS event_key_set(event_key);

    IF event_keys <> expected_keys_without_confirmation
       AND event_keys <> expected_keys_with_confirmation THEN
        RETURN false;
    END IF;

    event_data := event_envelope -> 'data';
    IF jsonb_typeof(event_data) <> 'object' THEN
        RETURN false;
    END IF;

    SELECT array_agg(data_key ORDER BY data_key)
    INTO data_keys
    FROM jsonb_object_keys(event_data) AS data_key_set(data_key);
    IF data_keys <> ARRAY['high_impact', 'result_code']::text[] THEN
        RETURN false;
    END IF;

    IF event_envelope ->> 'specversion' <> '1.0'
       OR event_envelope ->> 'datacontenttype' <> 'application/json'
       OR event_envelope ->> 'id' <> p_audit_event_record_id::text
       OR event_envelope ->> 'orgmetratenant' <> p_tenant_record_id::text THEN
        RETURN false;
    END IF;

    IF jsonb_typeof(event_envelope -> 'id') <> 'string'
       OR jsonb_typeof(event_envelope -> 'source') <> 'string'
       OR jsonb_typeof(event_envelope -> 'type') <> 'string'
       OR jsonb_typeof(event_envelope -> 'subject') <> 'string'
       OR jsonb_typeof(event_envelope -> 'time') <> 'string'
       OR jsonb_typeof(event_envelope -> 'orgmetraactor') <> 'string'
       OR jsonb_typeof(event_envelope -> 'orgmetrapurpose') <> 'string'
       OR jsonb_typeof(event_envelope -> 'orgmetrareason') <> 'string'
       OR jsonb_typeof(event_envelope -> 'orgmetraevidence') <> 'string'
       OR jsonb_typeof(event_data -> 'result_code') <> 'string'
       OR jsonb_typeof(event_data -> 'high_impact') <> 'boolean' THEN
        RETURN false;
    END IF;

    IF event_envelope ->> 'source' !~ '^urn:orgmetra:[a-z][a-z0-9]*(?:_[a-z0-9]+)+$'
       OR event_envelope ->> 'type' !~ '^orgmetra(?:\.[a-z][a-z0-9_]*){2,}$'
       OR event_envelope ->> 'subject' !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$'
       OR event_envelope ->> 'orgmetraactor' !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$'
       OR event_envelope ->> 'orgmetrapurpose' !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
       OR event_envelope ->> 'orgmetrareason' !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
       OR event_envelope ->> 'orgmetraevidence' !~ '^[A-Za-z0-9][A-Za-z0-9._:-]*$'
       OR event_data ->> 'result_code' !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$' THEN
        RETURN false;
    END IF;

    IF event_envelope ->> 'time' !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$' THEN
        RETURN false;
    END IF;
    BEGIN
        event_time := (event_envelope ->> 'time')::timestamptz;
    EXCEPTION
        WHEN others THEN
            RETURN false;
    END;
    IF event_time IS NULL THEN
        RETURN false;
    END IF;

    event_high_impact := (event_data ->> 'high_impact')::boolean;
    IF event_high_impact THEN
        IF NOT (event_envelope ? 'orgmetraconfirmation')
           OR jsonb_typeof(event_envelope -> 'orgmetraconfirmation') <> 'string'
           OR event_envelope ->> 'orgmetraconfirmation'
              !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$' THEN
            RETURN false;
        END IF;
    ELSIF event_envelope ? 'orgmetraconfirmation' THEN
        IF jsonb_typeof(event_envelope -> 'orgmetraconfirmation') <> 'string'
           OR event_envelope ->> 'orgmetraconfirmation'
              !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$' THEN
            RETURN false;
        END IF;
    END IF;

    IF p_event_envelope_digest !~ '^[0-9a-f]{64}$'
       OR encode(
            digest(convert_to(p_canonical_event_json, 'UTF8'), 'sha256'),
            'hex'
          ) <> p_event_envelope_digest THEN
        RETURN false;
    END IF;

    RETURN true;
END;
$$;

CREATE TABLE audit_event_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    audit_event_record_id uuid PRIMARY KEY,
    canonical_event_json text NOT NULL,
    digest_algorithm_code text NOT NULL DEFAULT 'sha256',
    event_envelope_digest text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT audit_event_tenant_operational_uuid_check
        CHECK (is_operational_uuid(tenant_record_id)),
    CONSTRAINT audit_event_record_operational_uuid_check
        CHECK (is_operational_uuid(audit_event_record_id)),
    CONSTRAINT audit_event_tenant_identity_unique
        UNIQUE (tenant_record_id, audit_event_record_id),
    CONSTRAINT audit_event_digest_algorithm_check
        CHECK (digest_algorithm_code = 'sha256'),
    CONSTRAINT audit_event_digest_format_check
        CHECK (event_envelope_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT audit_event_envelope_validation_check
        CHECK (
            validate_audit_event_envelope(
                canonical_event_json,
                audit_event_record_id,
                tenant_record_id,
                event_envelope_digest
            )
        )
);

CREATE TABLE outbox_delivery_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    outbox_delivery_record_id uuid PRIMARY KEY,
    audit_event_record_id uuid NOT NULL,
    delivery_target_code text NOT NULL,
    delivery_state_code text NOT NULL DEFAULT 'pending',
    delivery_attempt_count integer NOT NULL DEFAULT 0,
    available_at timestamptz NOT NULL DEFAULT now(),
    lease_owner_reference text,
    lease_expires_at timestamptz,
    last_failure_code text,
    delivered_at timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT outbox_delivery_tenant_operational_uuid_check
        CHECK (is_operational_uuid(tenant_record_id)),
    CONSTRAINT outbox_delivery_record_operational_uuid_check
        CHECK (is_operational_uuid(outbox_delivery_record_id)),
    CONSTRAINT outbox_delivery_audit_operational_uuid_check
        CHECK (is_operational_uuid(audit_event_record_id)),
    CONSTRAINT outbox_delivery_event_tenant_fk
        FOREIGN KEY (tenant_record_id, audit_event_record_id)
        REFERENCES audit_event_record(tenant_record_id, audit_event_record_id),
    CONSTRAINT outbox_delivery_tenant_identity_unique
        UNIQUE (tenant_record_id, outbox_delivery_record_id),
    CONSTRAINT outbox_delivery_event_target_unique
        UNIQUE (tenant_record_id, audit_event_record_id, delivery_target_code),
    CONSTRAINT outbox_delivery_target_code_check
        CHECK (delivery_target_code ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$'),
    CONSTRAINT outbox_delivery_state_code_check
        CHECK (delivery_state_code IN ('pending', 'leased', 'delivered')),
    CONSTRAINT outbox_delivery_attempt_count_check
        CHECK (delivery_attempt_count >= 0),
    CONSTRAINT outbox_delivery_lease_owner_check
        CHECK (
            lease_owner_reference IS NULL
            OR lease_owner_reference ~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$'
        ),
    CONSTRAINT outbox_delivery_failure_code_check
        CHECK (
            last_failure_code IS NULL
            OR last_failure_code ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
        ),
    CONSTRAINT outbox_delivery_state_shape_check
        CHECK (
            (
                delivery_state_code = 'pending'
                AND lease_owner_reference IS NULL
                AND lease_expires_at IS NULL
                AND delivered_at IS NULL
            )
            OR
            (
                delivery_state_code = 'leased'
                AND delivery_attempt_count > 0
                AND lease_owner_reference IS NOT NULL
                AND lease_expires_at IS NOT NULL
                AND delivered_at IS NULL
            )
            OR
            (
                delivery_state_code = 'delivered'
                AND delivery_attempt_count > 0
                AND lease_owner_reference IS NULL
                AND lease_expires_at IS NULL
                AND delivered_at IS NOT NULL
            )
        )
);

CREATE FUNCTION reject_audit_event_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'audit event records are append-only'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER audit_event_record_append_only_guard
BEFORE UPDATE OR DELETE ON audit_event_record
FOR EACH ROW
EXECUTE FUNCTION reject_audit_event_mutation();

CREATE FUNCTION protect_outbox_delivery_transition()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'outbox delivery records cannot be deleted'
            USING ERRCODE = '55000';
    END IF;

    IF NEW.tenant_record_id <> OLD.tenant_record_id
       OR NEW.outbox_delivery_record_id <> OLD.outbox_delivery_record_id
       OR NEW.audit_event_record_id <> OLD.audit_event_record_id
       OR NEW.delivery_target_code <> OLD.delivery_target_code
       OR NEW.recorded_at <> OLD.recorded_at THEN
        RAISE EXCEPTION 'outbox delivery identity and audit binding are immutable'
            USING ERRCODE = '55000';
    END IF;

    IF OLD.delivery_state_code = 'delivered' THEN
        RAISE EXCEPTION 'delivered outbox records are immutable'
            USING ERRCODE = '55000';
    END IF;

    IF OLD.delivery_state_code = 'pending' THEN
        IF NEW.delivery_state_code <> 'leased' THEN
            RAISE EXCEPTION 'outbox delivery must transition pending -> leased before completion'
                USING ERRCODE = '55000';
        END IF;
        IF NEW.delivery_attempt_count <> OLD.delivery_attempt_count + 1
           OR NEW.lease_owner_reference IS NULL
           OR NEW.lease_expires_at IS NULL
           OR NEW.delivered_at IS NOT NULL
           OR NEW.available_at <> OLD.available_at
           OR NEW.last_failure_code IS DISTINCT FROM OLD.last_failure_code THEN
            RAISE EXCEPTION 'leasing an outbox delivery may only set lease metadata and increment attempt count once'
                USING ERRCODE = '55000';
        END IF;
        RETURN NEW;
    END IF;

    IF OLD.delivery_state_code = 'leased' AND NEW.delivery_state_code = 'pending' THEN
        IF NEW.delivery_attempt_count <> OLD.delivery_attempt_count
           OR NEW.lease_owner_reference IS NOT NULL
           OR NEW.lease_expires_at IS NOT NULL
           OR NEW.delivered_at IS NOT NULL
           OR NEW.last_failure_code IS NULL
           OR NEW.available_at < OLD.available_at THEN
            RAISE EXCEPTION 'retry transition requires cleared lease, stable attempt count, failure code, and nondecreasing availability'
                USING ERRCODE = '55000';
        END IF;
        RETURN NEW;
    END IF;

    IF OLD.delivery_state_code = 'leased' AND NEW.delivery_state_code = 'delivered' THEN
        IF NEW.delivery_attempt_count <> OLD.delivery_attempt_count
           OR NEW.lease_owner_reference IS NOT NULL
           OR NEW.lease_expires_at IS NOT NULL
           OR NEW.delivered_at IS NULL
           OR NEW.available_at <> OLD.available_at THEN
            RAISE EXCEPTION 'delivery completion requires cleared lease and terminal delivery timestamp'
                USING ERRCODE = '55000';
        END IF;
        RETURN NEW;
    END IF;

    RAISE EXCEPTION 'outbox delivery transition is not permitted'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER outbox_delivery_transition_guard
BEFORE UPDATE OR DELETE ON outbox_delivery_record
FOR EACH ROW
EXECUTE FUNCTION protect_outbox_delivery_transition();

CREATE FUNCTION record_audit_outbox_event(
    p_tenant_record_id uuid,
    p_audit_event_record_id uuid,
    p_outbox_delivery_record_id uuid,
    p_canonical_event_json text,
    p_event_envelope_digest text,
    p_delivery_target_code text
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    IF is_operational_uuid(p_tenant_record_id) IS NOT TRUE
       OR is_operational_uuid(p_audit_event_record_id) IS NOT TRUE
       OR is_operational_uuid(p_outbox_delivery_record_id) IS NOT TRUE THEN
        RAISE EXCEPTION 'audit/outbox identity uses reserved UUID sentinel'
            USING ERRCODE = '23514';
    END IF;

    IF NOT validate_audit_event_envelope(
        p_canonical_event_json,
        p_audit_event_record_id,
        p_tenant_record_id,
        p_event_envelope_digest
    ) THEN
        RAISE EXCEPTION 'audit event envelope failed database validation'
            USING ERRCODE = '23514';
    END IF;

    INSERT INTO audit_event_record (
        tenant_record_id,
        audit_event_record_id,
        canonical_event_json,
        digest_algorithm_code,
        event_envelope_digest
    ) VALUES (
        p_tenant_record_id,
        p_audit_event_record_id,
        p_canonical_event_json,
        'sha256',
        p_event_envelope_digest
    );

    INSERT INTO outbox_delivery_record (
        tenant_record_id,
        outbox_delivery_record_id,
        audit_event_record_id,
        delivery_target_code
    ) VALUES (
        p_tenant_record_id,
        p_outbox_delivery_record_id,
        p_audit_event_record_id,
        p_delivery_target_code
    );
END;
$$;

ALTER TABLE audit_event_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_event_record FORCE ROW LEVEL SECURITY;
CREATE POLICY audit_event_record_scope_policy ON audit_event_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE outbox_delivery_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox_delivery_record FORCE ROW LEVEL SECURITY;
CREATE POLICY outbox_delivery_record_scope_policy ON outbox_delivery_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());
