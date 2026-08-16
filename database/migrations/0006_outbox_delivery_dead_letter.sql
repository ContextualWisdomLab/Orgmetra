-- Add a governed terminal dead-letter boundary for dispatcher work that has
-- exhausted an explicit retry budget. The mutable queue row records only
-- terminal transport state; immutable escalation evidence is normalized into
-- its own append-only tenant-scoped record.

ALTER TABLE outbox_delivery_record
DROP CONSTRAINT outbox_delivery_state_code_check;

ALTER TABLE outbox_delivery_record
ADD CONSTRAINT outbox_delivery_state_code_check
CHECK (delivery_state_code IN ('pending', 'leased', 'delivered', 'dead_lettered'));

ALTER TABLE outbox_delivery_record
DROP CONSTRAINT outbox_delivery_state_shape_check;

ALTER TABLE outbox_delivery_record
ADD CONSTRAINT outbox_delivery_state_shape_check
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
    OR
    (
        delivery_state_code = 'dead_lettered'
        AND delivery_attempt_count > 0
        AND lease_owner_reference IS NULL
        AND lease_expires_at IS NULL
        AND last_failure_code IS NOT NULL
        AND delivered_at IS NULL
    )
);

CREATE TABLE outbox_delivery_escalation_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    outbox_delivery_escalation_record_id uuid PRIMARY KEY,
    outbox_delivery_record_id uuid NOT NULL,
    failure_code text NOT NULL,
    escalation_reference text NOT NULL,
    terminal_attempt_count integer NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT outbox_escalation_tenant_operational_uuid_check
        CHECK (is_operational_uuid(tenant_record_id)),
    CONSTRAINT outbox_escalation_record_operational_uuid_check
        CHECK (is_operational_uuid(outbox_delivery_escalation_record_id)),
    CONSTRAINT outbox_escalation_delivery_operational_uuid_check
        CHECK (is_operational_uuid(outbox_delivery_record_id)),
    CONSTRAINT outbox_escalation_delivery_tenant_fk
        FOREIGN KEY (tenant_record_id, outbox_delivery_record_id)
        REFERENCES outbox_delivery_record(tenant_record_id, outbox_delivery_record_id),
    CONSTRAINT outbox_escalation_delivery_unique
        UNIQUE (tenant_record_id, outbox_delivery_record_id),
    CONSTRAINT outbox_escalation_failure_code_check
        CHECK (failure_code ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'),
    CONSTRAINT outbox_escalation_reference_check
        CHECK (
            escalation_reference
            ~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$'
        ),
    CONSTRAINT outbox_escalation_attempt_count_check
        CHECK (terminal_attempt_count > 0)
);

CREATE FUNCTION reject_outbox_delivery_escalation_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'outbox delivery escalation records are append-only'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER outbox_delivery_escalation_append_only_guard
BEFORE UPDATE OR DELETE ON outbox_delivery_escalation_record
FOR EACH ROW
EXECUTE FUNCTION reject_outbox_delivery_escalation_mutation();

ALTER TABLE outbox_delivery_escalation_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox_delivery_escalation_record FORCE ROW LEVEL SECURITY;
CREATE POLICY outbox_delivery_escalation_scope_policy
ON outbox_delivery_escalation_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

CREATE OR REPLACE FUNCTION protect_outbox_delivery_transition()
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

    IF OLD.delivery_state_code IN ('delivered', 'dead_lettered') THEN
        RAISE EXCEPTION 'terminal outbox delivery records are immutable'
            USING ERRCODE = '55000';
    END IF;

    IF OLD.delivery_state_code = 'pending' THEN
        IF NEW.delivery_state_code <> 'leased' THEN
            RAISE EXCEPTION 'outbox delivery must transition pending -> leased before completion'
                USING ERRCODE = '55000';
        END IF;
        IF NEW.lease_expires_at IS NOT NULL
           AND NEW.lease_expires_at <= transaction_timestamp() THEN
            RAISE EXCEPTION 'outbox lease expiry must be in the future'
                USING ERRCODE = '22023';
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

    IF OLD.delivery_state_code = 'leased' AND NEW.delivery_state_code = 'leased' THEN
        IF OLD.lease_expires_at IS NULL
           OR OLD.lease_expires_at > transaction_timestamp() THEN
            RAISE EXCEPTION 'live outbox lease cannot be replaced'
                USING ERRCODE = '55000';
        END IF;
        IF NEW.delivery_attempt_count <> OLD.delivery_attempt_count + 1
           OR NEW.lease_owner_reference IS NULL
           OR NEW.lease_expires_at IS NULL
           OR NEW.lease_expires_at <= transaction_timestamp()
           OR NEW.delivered_at IS NOT NULL
           OR NEW.available_at <> OLD.available_at
           OR NEW.last_failure_code IS DISTINCT FROM 'lease_expired' THEN
            RAISE EXCEPTION 'expired lease takeover requires a new future lease, one attempt increment, and lease-expired evidence'
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

    IF OLD.delivery_state_code = 'leased'
       AND NEW.delivery_state_code = 'dead_lettered' THEN
        IF NEW.delivery_attempt_count <> OLD.delivery_attempt_count
           OR NEW.lease_owner_reference IS NOT NULL
           OR NEW.lease_expires_at IS NOT NULL
           OR NEW.delivered_at IS NOT NULL
           OR NEW.available_at <> OLD.available_at
           OR NEW.last_failure_code IS NULL THEN
            RAISE EXCEPTION 'dead-letter transition requires cleared lease, stable attempts, and terminal failure evidence'
                USING ERRCODE = '55000';
        END IF;
        RETURN NEW;
    END IF;

    RAISE EXCEPTION 'outbox delivery transition is not permitted'
        USING ERRCODE = '55000';
END;
$$;

CREATE FUNCTION dead_letter_outbox_delivery(
    p_tenant_record_id uuid,
    p_outbox_delivery_record_id uuid,
    p_outbox_delivery_escalation_record_id uuid,
    p_lease_owner_reference text,
    p_failure_code text,
    p_escalation_reference text,
    p_max_attempt_count integer DEFAULT 5
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    current_state_code text;
    current_attempt_count integer;
    current_lease_owner_reference text;
    current_lease_expires_at timestamptz;
BEGIN
    IF is_operational_uuid(p_tenant_record_id) IS NOT TRUE
       OR is_operational_uuid(p_outbox_delivery_record_id) IS NOT TRUE
       OR is_operational_uuid(p_outbox_delivery_escalation_record_id) IS NOT TRUE THEN
        RAISE EXCEPTION 'outbox dead-letter identity uses a reserved UUID sentinel'
            USING ERRCODE = '23514';
    END IF;

    IF current_tenant_record_id() IS DISTINCT FROM p_tenant_record_id THEN
        RAISE EXCEPTION 'outbox dead-letter tenant context does not match requested tenant'
            USING ERRCODE = '42501';
    END IF;

    IF p_lease_owner_reference IS NULL
       OR p_lease_owner_reference !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$' THEN
        RAISE EXCEPTION 'lease owner must be a namespaced opaque reference'
            USING ERRCODE = '22023';
    END IF;

    IF p_failure_code IS NULL
       OR p_failure_code !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$' THEN
        RAISE EXCEPTION 'failure code must be a lower snake_case code'
            USING ERRCODE = '22023';
    END IF;

    IF p_escalation_reference IS NULL
       OR p_escalation_reference !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$' THEN
        RAISE EXCEPTION 'escalation reference must be a namespaced opaque reference'
            USING ERRCODE = '22023';
    END IF;

    IF p_max_attempt_count IS NULL
       OR p_max_attempt_count < 1
       OR p_max_attempt_count > 100 THEN
        RAISE EXCEPTION 'maximum attempt count must be between 1 and 100'
            USING ERRCODE = '22023';
    END IF;

    SELECT
        delivery_record.delivery_state_code,
        delivery_record.delivery_attempt_count,
        delivery_record.lease_owner_reference,
        delivery_record.lease_expires_at
    INTO
        current_state_code,
        current_attempt_count,
        current_lease_owner_reference,
        current_lease_expires_at
    FROM outbox_delivery_record AS delivery_record
    WHERE delivery_record.tenant_record_id = p_tenant_record_id
      AND delivery_record.outbox_delivery_record_id = p_outbox_delivery_record_id
    FOR UPDATE OF delivery_record;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'outbox delivery record not found'
            USING ERRCODE = 'P0002';
    END IF;

    IF current_state_code <> 'leased' THEN
        RAISE EXCEPTION 'outbox delivery is not leased'
            USING ERRCODE = '55000';
    END IF;

    IF current_lease_owner_reference IS DISTINCT FROM p_lease_owner_reference THEN
        RAISE EXCEPTION 'outbox lease is not owned by caller'
            USING ERRCODE = '42501';
    END IF;

    IF current_lease_expires_at IS NULL
       OR current_lease_expires_at <= transaction_timestamp() THEN
        RAISE EXCEPTION 'outbox lease is expired and must be reclaimed'
            USING ERRCODE = '55000';
    END IF;

    IF current_attempt_count < p_max_attempt_count THEN
        RAISE EXCEPTION 'outbox delivery attempt budget is not exhausted'
            USING ERRCODE = '55000';
    END IF;

    INSERT INTO outbox_delivery_escalation_record (
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
        p_escalation_reference,
        current_attempt_count
    );

    UPDATE outbox_delivery_record AS delivery_record
    SET delivery_state_code = 'dead_lettered',
        lease_owner_reference = NULL,
        lease_expires_at = NULL,
        last_failure_code = p_failure_code
    WHERE delivery_record.tenant_record_id = p_tenant_record_id
      AND delivery_record.outbox_delivery_record_id = p_outbox_delivery_record_id;
END;
$$;
