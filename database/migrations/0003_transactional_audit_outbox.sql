-- Persist exact governed event bytes in the same transaction as an Orgmetra write.
-- The record is append-only and tenant-scoped. Delivery leases/retries are a
-- separate operational concern so dispatch state cannot mutate audit evidence.

CREATE TABLE audit_outbox_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    audit_outbox_record_id uuid PRIMARY KEY,
    event_id uuid NOT NULL,
    event_envelope_text text NOT NULL,
    digest_algorithm_code text NOT NULL DEFAULT 'sha256',
    event_content_digest text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT audit_outbox_record_id_not_nil_check
        CHECK (audit_outbox_record_id <> '00000000-0000-0000-0000-000000000000'::uuid),
    CONSTRAINT audit_outbox_event_id_not_nil_check
        CHECK (event_id <> '00000000-0000-0000-0000-000000000000'::uuid),
    CONSTRAINT audit_outbox_envelope_not_blank_check
        CHECK (btrim(event_envelope_text) <> ''),
    CONSTRAINT audit_outbox_digest_algorithm_check
        CHECK (digest_algorithm_code = 'sha256'),
    CONSTRAINT audit_outbox_digest_format_check
        CHECK (event_content_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT audit_outbox_tenant_identity_unique
        UNIQUE (tenant_record_id, audit_outbox_record_id),
    CONSTRAINT audit_outbox_tenant_event_unique
        UNIQUE (tenant_record_id, event_id)
);

CREATE FUNCTION validate_audit_outbox_insert()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    parsed_envelope jsonb;
    computed_digest text;
    high_impact_value boolean;
BEGIN
    BEGIN
        parsed_envelope := NEW.event_envelope_text::jsonb;
    EXCEPTION WHEN others THEN
        RAISE EXCEPTION 'audit outbox envelope must be valid JSON'
            USING ERRCODE = '22023';
    END;

    IF jsonb_typeof(parsed_envelope) <> 'object' THEN
        RAISE EXCEPTION 'audit outbox envelope must be a JSON object'
            USING ERRCODE = '23514';
    END IF;

    IF parsed_envelope ->> 'specversion' IS DISTINCT FROM '1.0'
       OR parsed_envelope ->> 'datacontenttype' IS DISTINCT FROM 'application/json'
       OR parsed_envelope ->> 'id' IS DISTINCT FROM NEW.event_id::text THEN
        RAISE EXCEPTION 'audit outbox envelope does not match its CloudEvents identity contract'
            USING ERRCODE = '23514';
    END IF;

    IF parsed_envelope ->> 'orgmetratenant' IS DISTINCT FROM NEW.tenant_record_id::text THEN
        RAISE EXCEPTION 'audit envelope tenant does not match owning tenant'
            USING ERRCODE = '23514';
    END IF;

    IF NULLIF(btrim(parsed_envelope ->> 'source'), '') IS NULL
       OR NULLIF(btrim(parsed_envelope ->> 'type'), '') IS NULL
       OR NULLIF(btrim(parsed_envelope ->> 'subject'), '') IS NULL
       OR NULLIF(btrim(parsed_envelope ->> 'time'), '') IS NULL
       OR NULLIF(btrim(parsed_envelope ->> 'orgmetraactor'), '') IS NULL
       OR NULLIF(btrim(parsed_envelope ->> 'orgmetrapurpose'), '') IS NULL
       OR NULLIF(btrim(parsed_envelope ->> 'orgmetrareason'), '') IS NULL
       OR NULLIF(btrim(parsed_envelope ->> 'orgmetraevidence'), '') IS NULL THEN
        RAISE EXCEPTION 'audit outbox envelope is missing required governance metadata'
            USING ERRCODE = '23514';
    END IF;

    IF jsonb_typeof(parsed_envelope -> 'data') IS DISTINCT FROM 'object'
       OR jsonb_typeof(parsed_envelope #> '{data,high_impact}') IS DISTINCT FROM 'boolean'
       OR NULLIF(btrim(parsed_envelope #>> '{data,result_code}'), '') IS NULL THEN
        RAISE EXCEPTION 'audit outbox envelope has invalid governed result data'
            USING ERRCODE = '23514';
    END IF;

    high_impact_value := (parsed_envelope #>> '{data,high_impact}')::boolean;
    IF high_impact_value
       AND NULLIF(btrim(parsed_envelope ->> 'orgmetraconfirmation'), '') IS NULL THEN
        RAISE EXCEPTION 'high-impact audit envelope requires accountable human confirmation'
            USING ERRCODE = '23514';
    END IF;

    computed_digest := encode(
        digest(convert_to(NEW.event_envelope_text, 'UTF8'), 'sha256'),
        'hex'
    );
    IF NEW.event_content_digest IS DISTINCT FROM computed_digest THEN
        RAISE EXCEPTION 'audit outbox digest does not match exact envelope bytes'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER audit_outbox_insert_validation_guard
BEFORE INSERT ON audit_outbox_record
FOR EACH ROW
EXECUTE FUNCTION validate_audit_outbox_insert();

CREATE TRIGGER audit_outbox_append_only_guard
BEFORE UPDATE OR DELETE ON audit_outbox_record
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

ALTER TABLE audit_outbox_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_outbox_record FORCE ROW LEVEL SECURITY;
CREATE POLICY audit_outbox_scope_policy ON audit_outbox_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());
