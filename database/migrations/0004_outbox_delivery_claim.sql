-- Add one bounded dispatcher claim boundary without weakening immutable audit
-- evidence. PostgreSQL row locking is the concurrency primitive: eligible queue
-- rows are selected in deterministic order and locked with SKIP LOCKED so
-- independent consumers can claim distinct work without convoying on a live
-- claim. Expired leases are eligible for atomic takeover so a crashed worker
-- cannot strand delivery indefinitely. All caller-supplied identity/context
-- values fail closed before DML.

CREATE INDEX outbox_delivery_claim_candidate_idx
ON outbox_delivery_record (
    tenant_record_id,
    delivery_target_code,
    available_at,
    recorded_at,
    outbox_delivery_record_id
)
WHERE delivery_state_code = 'pending';

CREATE INDEX outbox_delivery_expired_lease_idx
ON outbox_delivery_record (
    tenant_record_id,
    delivery_target_code,
    lease_expires_at,
    recorded_at,
    outbox_delivery_record_id
)
WHERE delivery_state_code = 'leased';

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

    IF OLD.delivery_state_code = 'delivered' THEN
        RAISE EXCEPTION 'delivered outbox records are immutable'
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

    RAISE EXCEPTION 'outbox delivery transition is not permitted'
        USING ERRCODE = '55000';
END;
$$;

CREATE FUNCTION claim_outbox_delivery(
    p_tenant_record_id uuid,
    p_delivery_target_code text,
    p_lease_owner_reference text,
    p_lease_duration_seconds integer DEFAULT 300
)
RETURNS TABLE (
    outbox_delivery_record_id uuid,
    audit_event_record_id uuid,
    delivery_target_code text,
    delivery_attempt_count integer,
    lease_owner_reference text,
    lease_expires_at timestamptz,
    canonical_event_json text,
    event_envelope_digest text
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF is_operational_uuid(p_tenant_record_id) IS NOT TRUE THEN
        RAISE EXCEPTION 'outbox claim tenant identity uses a reserved UUID sentinel'
            USING ERRCODE = '23514';
    END IF;

    IF current_tenant_record_id() IS DISTINCT FROM p_tenant_record_id THEN
        RAISE EXCEPTION 'outbox claim tenant context does not match requested tenant'
            USING ERRCODE = '42501';
    END IF;

    IF p_delivery_target_code IS NULL
       OR p_delivery_target_code !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$' THEN
        RAISE EXCEPTION 'delivery target must contain two or more lower snake_case words'
            USING ERRCODE = '22023';
    END IF;

    IF p_lease_owner_reference IS NULL
       OR p_lease_owner_reference !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$' THEN
        RAISE EXCEPTION 'lease owner must be a namespaced opaque reference'
            USING ERRCODE = '22023';
    END IF;

    IF p_lease_duration_seconds IS NULL
       OR p_lease_duration_seconds < 1
       OR p_lease_duration_seconds > 3600 THEN
        RAISE EXCEPTION 'lease duration must be between 1 and 3600 seconds'
            USING ERRCODE = '22023';
    END IF;

    RETURN QUERY
    WITH candidate_delivery AS MATERIALIZED (
        SELECT delivery_record.outbox_delivery_record_id
        FROM outbox_delivery_record AS delivery_record
        WHERE delivery_record.tenant_record_id = p_tenant_record_id
          AND delivery_record.delivery_target_code = p_delivery_target_code
          AND (
              (
                  delivery_record.delivery_state_code = 'pending'
                  AND delivery_record.available_at <= transaction_timestamp()
              )
              OR
              (
                  delivery_record.delivery_state_code = 'leased'
                  AND delivery_record.lease_expires_at <= transaction_timestamp()
              )
          )
        ORDER BY
            delivery_record.available_at,
            delivery_record.recorded_at,
            delivery_record.outbox_delivery_record_id
        FOR UPDATE OF delivery_record SKIP LOCKED
        LIMIT 1
    ),
    leased_delivery AS (
        UPDATE outbox_delivery_record AS delivery_record
        SET delivery_state_code = 'leased',
            delivery_attempt_count = delivery_record.delivery_attempt_count + 1,
            lease_owner_reference = p_lease_owner_reference,
            lease_expires_at = transaction_timestamp()
                + make_interval(secs => p_lease_duration_seconds),
            last_failure_code = CASE
                WHEN delivery_record.delivery_state_code = 'leased'
                    THEN 'lease_expired'
                ELSE delivery_record.last_failure_code
            END
        FROM candidate_delivery AS candidate_record
        WHERE delivery_record.outbox_delivery_record_id
              = candidate_record.outbox_delivery_record_id
        RETURNING
            delivery_record.tenant_record_id,
            delivery_record.outbox_delivery_record_id,
            delivery_record.audit_event_record_id,
            delivery_record.delivery_target_code,
            delivery_record.delivery_attempt_count,
            delivery_record.lease_owner_reference,
            delivery_record.lease_expires_at
    )
    SELECT
        leased_record.outbox_delivery_record_id,
        leased_record.audit_event_record_id,
        leased_record.delivery_target_code,
        leased_record.delivery_attempt_count,
        leased_record.lease_owner_reference,
        leased_record.lease_expires_at,
        audit_record.canonical_event_json,
        audit_record.event_envelope_digest
    FROM leased_delivery AS leased_record
    JOIN audit_event_record AS audit_record
      ON audit_record.tenant_record_id = leased_record.tenant_record_id
     AND audit_record.audit_event_record_id = leased_record.audit_event_record_id;
END;
$$;
