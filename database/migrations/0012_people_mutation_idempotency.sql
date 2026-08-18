-- Persist People mutation Idempotency-Key bindings with the authoritative write.
--
-- HTTP retries allocate fresh record identifiers. The write port therefore
-- stores one tenant-scoped command digest for each route and key inside the
-- same transaction as the HRIS fact and audit/outbox pair. A matching replay
-- returns the first committed identity. A changed command under the same key
-- cannot insert a second row.

BEGIN;

SET LOCAL search_path = public, pg_catalog;

CREATE TABLE people_mutation_idempotency_record (
    tenant_record_id uuid NOT NULL REFERENCES public.tenant_record(tenant_record_id),
    people_mutation_idempotency_record_id uuid PRIMARY KEY,
    command_route text NOT NULL,
    idempotency_key text NOT NULL,
    command_digest text NOT NULL,
    created_record_id uuid NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    CONSTRAINT people_mutation_idempotency_record_id_operational_check
        CHECK (public.is_operational_uuid(people_mutation_idempotency_record_id)),
    CONSTRAINT people_mutation_idempotency_created_record_operational_check
        CHECK (public.is_operational_uuid(created_record_id)),
    CONSTRAINT people_mutation_idempotency_route_check
        CHECK (
            command_route IN (
                'candidate-worker-conversions',
                'employment-records',
                'position-records',
                'assignment-records'
            )
        ),
    CONSTRAINT people_mutation_idempotency_key_check
        CHECK (
            char_length(idempotency_key) BETWEEN 16 AND 200
            AND idempotency_key ~ '^[\x21-\x7E]+$'
        ),
    CONSTRAINT people_mutation_idempotency_digest_check
        CHECK (command_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT people_mutation_idempotency_tenant_identity_unique
        UNIQUE (tenant_record_id, people_mutation_idempotency_record_id),
    CONSTRAINT people_mutation_idempotency_command_unique
        UNIQUE (tenant_record_id, command_route, idempotency_key)
);

CREATE TRIGGER people_mutation_idempotency_append_only_guard
BEFORE UPDATE OR DELETE ON people_mutation_idempotency_record
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

CREATE FUNCTION public.reject_people_mutation_idempotency_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'people mutation idempotency records cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER people_mutation_idempotency_truncate_guard
BEFORE TRUNCATE ON people_mutation_idempotency_record
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_people_mutation_idempotency_truncate();

REVOKE TRUNCATE ON people_mutation_idempotency_record FROM PUBLIC;

ALTER TABLE people_mutation_idempotency_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE people_mutation_idempotency_record FORCE ROW LEVEL SECURITY;
CREATE POLICY people_mutation_idempotency_scope_policy ON people_mutation_idempotency_record
USING (tenant_record_id = public.current_tenant_record_id())
WITH CHECK (tenant_record_id = public.current_tenant_record_id());

COMMIT;