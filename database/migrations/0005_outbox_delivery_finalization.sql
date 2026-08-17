-- Finalize or retry an outbox delivery only while the caller still owns a
-- live lease. Claim ownership is an executable capability boundary: merely
-- knowing a delivery identifier is insufficient to acknowledge or release it.

CREATE FUNCTION complete_outbox_delivery(
    p_tenant_record_id uuid,
    p_outbox_delivery_record_id uuid,
    p_lease_owner_reference text
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    current_state_code text;
    current_lease_owner_reference text;
    current_lease_expires_at timestamptz;
BEGIN
    IF is_operational_uuid(p_tenant_record_id) IS NOT TRUE
       OR is_operational_uuid(p_outbox_delivery_record_id) IS NOT TRUE THEN
        RAISE EXCEPTION 'outbox finalization identity uses a reserved UUID sentinel'
            USING ERRCODE = '23514';
    END IF;

    IF current_tenant_record_id() IS DISTINCT FROM p_tenant_record_id THEN
        RAISE EXCEPTION 'outbox finalization tenant context does not match requested tenant'
            USING ERRCODE = '42501';
    END IF;

    IF p_lease_owner_reference IS NULL
       OR p_lease_owner_reference !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$' THEN
        RAISE EXCEPTION 'lease owner must be a namespaced opaque reference'
            USING ERRCODE = '22023';
    END IF;

    SELECT
        delivery_record.delivery_state_code,
        delivery_record.lease_owner_reference,
        delivery_record.lease_expires_at
    INTO
        current_state_code,
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

    UPDATE outbox_delivery_record AS delivery_record
    SET delivery_state_code = 'delivered',
        lease_owner_reference = NULL,
        lease_expires_at = NULL,
        delivered_at = transaction_timestamp()
    WHERE delivery_record.tenant_record_id = p_tenant_record_id
      AND delivery_record.outbox_delivery_record_id = p_outbox_delivery_record_id;
END;
$$;

CREATE FUNCTION retry_outbox_delivery(
    p_tenant_record_id uuid,
    p_outbox_delivery_record_id uuid,
    p_lease_owner_reference text,
    p_failure_code text,
    p_retry_delay_seconds integer DEFAULT 60
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    current_state_code text;
    current_lease_owner_reference text;
    current_lease_expires_at timestamptz;
BEGIN
    IF is_operational_uuid(p_tenant_record_id) IS NOT TRUE
       OR is_operational_uuid(p_outbox_delivery_record_id) IS NOT TRUE THEN
        RAISE EXCEPTION 'outbox retry identity uses a reserved UUID sentinel'
            USING ERRCODE = '23514';
    END IF;

    IF current_tenant_record_id() IS DISTINCT FROM p_tenant_record_id THEN
        RAISE EXCEPTION 'outbox retry tenant context does not match requested tenant'
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

    IF p_retry_delay_seconds IS NULL
       OR p_retry_delay_seconds < 1
       OR p_retry_delay_seconds > 86400 THEN
        RAISE EXCEPTION 'retry delay must be between 1 and 86400 seconds'
            USING ERRCODE = '22023';
    END IF;

    SELECT
        delivery_record.delivery_state_code,
        delivery_record.lease_owner_reference,
        delivery_record.lease_expires_at
    INTO
        current_state_code,
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

    UPDATE outbox_delivery_record AS delivery_record
    SET delivery_state_code = 'pending',
        lease_owner_reference = NULL,
        lease_expires_at = NULL,
        last_failure_code = p_failure_code,
        available_at = GREATEST(
            delivery_record.available_at,
            transaction_timestamp() + make_interval(secs => p_retry_delay_seconds)
        )
    WHERE delivery_record.tenant_record_id = p_tenant_record_id
      AND delivery_record.outbox_delivery_record_id = p_outbox_delivery_record_id;
END;
$$;
