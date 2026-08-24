-- Persist value-minimized HR document metadata inside the document_records owner
-- boundary. Cross-service Person/Employment/audit/outbox identities remain
-- opaque published-contract references rather than direct application-table SQL.

CREATE TABLE document_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    document_record_id uuid PRIMARY KEY,
    document_record_reference text NOT NULL,
    person_record_reference text NOT NULL,
    employment_record_reference text NOT NULL,
    uploader_actor_reference text NOT NULL,
    persisted_by_actor_reference text NOT NULL,
    document_category_code text NOT NULL,
    artifact_reference text NOT NULL,
    artifact_digest_sha256 text NOT NULL,
    source_provenance_digest_sha256 text NOT NULL,
    retention_policy_reference text NOT NULL,
    retention_policy_digest_sha256 text NOT NULL,
    received_at timestamptz NOT NULL,
    canonical_evidence_json text NOT NULL,
    evidence_digest_sha256 text NOT NULL,
    audit_event_reference text NOT NULL,
    outbox_event_reference text NOT NULL,
    application_evidence_digest_sha256 text NOT NULL,
    application_purpose_code text NOT NULL DEFAULT 'document_record_persist',
    application_reason_code text NOT NULL DEFAULT 'reviewed_document_metadata',
    classification_code text NOT NULL DEFAULT 'restricted_hr',
    content_storage_state text NOT NULL DEFAULT 'artifact_reference_only',
    decision_authority_state text NOT NULL DEFAULT 'not_authorized_for_employment_decision',
    recorded_at timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),

    CONSTRAINT document_record_id_operational_check
        CHECK (public.is_operational_uuid(document_record_id)),
    CONSTRAINT document_record_reference_check
        CHECK (
            document_record_reference ~
            '^document_record:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT document_person_record_reference_check
        CHECK (
            person_record_reference ~
            '^person_record:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT document_employment_record_reference_check
        CHECK (
            employment_record_reference ~
            '^employment_record:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT document_uploader_actor_reference_check
        CHECK (
            uploader_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT document_persisted_actor_reference_check
        CHECK (
            persisted_by_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT document_category_code_check
        CHECK (
            document_category_code IN (
                'employment_contract',
                'policy_acknowledgement',
                'qualification_document'
            )
        ),
    CONSTRAINT document_artifact_reference_check
        CHECK (
            artifact_reference ~
            '^document_artifact:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT document_artifact_digest_check
        CHECK (artifact_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT document_source_provenance_digest_check
        CHECK (source_provenance_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT document_retention_policy_reference_check
        CHECK (
            retention_policy_reference ~
            '^retention_policy:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT document_retention_policy_digest_check
        CHECK (retention_policy_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT document_canonical_evidence_size_check
        CHECK (
            octet_length(canonical_evidence_json) > 0
            AND octet_length(canonical_evidence_json) <= 4096
        ),
    CONSTRAINT document_evidence_digest_check
        CHECK (evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT document_audit_event_reference_check
        CHECK (
            audit_event_reference ~
            '^audit_event:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT document_outbox_event_reference_check
        CHECK (
            outbox_event_reference ~
            '^outbox_event:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT document_application_evidence_digest_check
        CHECK (application_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT document_application_purpose_code_check
        CHECK (application_purpose_code = 'document_record_persist'),
    CONSTRAINT document_application_reason_code_check
        CHECK (application_reason_code = 'reviewed_document_metadata'),
    CONSTRAINT document_classification_code_check
        CHECK (classification_code = 'restricted_hr'),
    CONSTRAINT document_content_storage_state_check
        CHECK (content_storage_state = 'artifact_reference_only'),
    CONSTRAINT document_decision_authority_state_check
        CHECK (decision_authority_state = 'not_authorized_for_employment_decision'),
    CONSTRAINT document_record_tenant_reference_unique
        UNIQUE (tenant_record_id, document_record_reference),
    CONSTRAINT document_record_tenant_artifact_unique
        UNIQUE (tenant_record_id, artifact_reference),
    CONSTRAINT document_record_tenant_audit_reference_unique
        UNIQUE (tenant_record_id, audit_event_reference),
    CONSTRAINT document_record_tenant_outbox_reference_unique
        UNIQUE (tenant_record_id, outbox_event_reference)
);

COMMENT ON TABLE document_record IS
    'Immutable, value-minimized HR document metadata owned by document_records. The exact canonical evidence snapshot is digest-bound to the typed row; Person, Employment, audit, and outbox identities are opaque contract references. Document bytes and employment-decision authority are not stored here.';

CREATE FUNCTION enforce_document_record_system_time()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.recorded_at IS DISTINCT FROM pg_catalog.transaction_timestamp() THEN
        RAISE EXCEPTION 'document-record recorded_at must equal the current transaction timestamp'
            USING ERRCODE = '22023';
    END IF;
    IF NEW.received_at > NEW.recorded_at THEN
        RAISE EXCEPTION 'document-record received_at cannot be later than recorded_at'
            USING ERRCODE = '22023';
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION enforce_document_record_system_time() IS
    'Requires PostgreSQL-owned system-recorded time and rejects document receipt time later than the durable recording instant.';

CREATE TRIGGER document_record_system_time_guard
BEFORE INSERT ON document_record
FOR EACH ROW
EXECUTE FUNCTION enforce_document_record_system_time();

CREATE FUNCTION validate_document_record_evidence_binding()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    evidence_payload jsonb;
    evidence_key_count integer;
    computed_evidence_digest text;
    evidence_received_at timestamptz;
    evidence_recorded_at timestamptz;
BEGIN
    computed_evidence_digest := encode(
        pg_catalog.digest(
            pg_catalog.convert_to(NEW.canonical_evidence_json, 'UTF8'),
            'sha256'
        ),
        'hex'
    );
    IF computed_evidence_digest IS DISTINCT FROM NEW.evidence_digest_sha256 THEN
        RAISE EXCEPTION 'document-record canonical evidence digest does not match the stored evidence bytes'
            USING ERRCODE = '23514';
    END IF;

    BEGIN
        evidence_payload := NEW.canonical_evidence_json::jsonb;
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'document-record canonical evidence must be valid JSON'
            USING ERRCODE = '22023';
    END;

    IF pg_catalog.jsonb_typeof(evidence_payload) IS DISTINCT FROM 'object' THEN
        RAISE EXCEPTION 'document-record canonical evidence must be one JSON object'
            USING ERRCODE = '23514';
    END IF;

    SELECT count(*)
    INTO evidence_key_count
    FROM pg_catalog.jsonb_object_keys(evidence_payload);

    IF evidence_key_count <> 17
       OR NOT (
           evidence_payload ?& ARRAY[
               'artifact_digest',
               'artifact_reference',
               'classification_code',
               'content_storage_state',
               'decision_authority_state',
               'document_category_code',
               'document_record_reference',
               'employment_record_reference',
               'person_record_reference',
               'received_at',
               'recorded_at',
               'retention_policy_digest',
               'retention_policy_reference',
               'schema_version',
               'source_provenance_digest',
               'tenant_record_id',
               'uploader_actor_reference'
           ]
       ) THEN
        RAISE EXCEPTION 'document-record canonical evidence has an unexpected key set'
            USING ERRCODE = '23514';
    END IF;

    IF evidence_payload ->> 'artifact_digest'
          IS DISTINCT FROM NEW.artifact_digest_sha256
       OR evidence_payload ->> 'artifact_reference'
          IS DISTINCT FROM NEW.artifact_reference
       OR evidence_payload ->> 'classification_code'
          IS DISTINCT FROM NEW.classification_code
       OR evidence_payload ->> 'content_storage_state'
          IS DISTINCT FROM NEW.content_storage_state
       OR evidence_payload ->> 'decision_authority_state'
          IS DISTINCT FROM NEW.decision_authority_state
       OR evidence_payload ->> 'document_category_code'
          IS DISTINCT FROM NEW.document_category_code
       OR evidence_payload ->> 'document_record_reference'
          IS DISTINCT FROM NEW.document_record_reference
       OR evidence_payload ->> 'employment_record_reference'
          IS DISTINCT FROM NEW.employment_record_reference
       OR evidence_payload ->> 'person_record_reference'
          IS DISTINCT FROM NEW.person_record_reference
       OR evidence_payload ->> 'retention_policy_digest'
          IS DISTINCT FROM NEW.retention_policy_digest_sha256
       OR evidence_payload ->> 'retention_policy_reference'
          IS DISTINCT FROM NEW.retention_policy_reference
       OR evidence_payload ->> 'schema_version'
          IS DISTINCT FROM 'orgmetra.document_record_evidence.v1'
       OR evidence_payload ->> 'source_provenance_digest'
          IS DISTINCT FROM NEW.source_provenance_digest_sha256
       OR evidence_payload ->> 'tenant_record_id'
          IS DISTINCT FROM NEW.tenant_record_id::text
       OR evidence_payload ->> 'uploader_actor_reference'
          IS DISTINCT FROM NEW.uploader_actor_reference THEN
        RAISE EXCEPTION 'document-record canonical evidence does not exactly match the typed metadata row'
            USING ERRCODE = '23514';
    END IF;

    BEGIN
        evidence_received_at := (evidence_payload ->> 'received_at')::timestamptz;
        evidence_recorded_at := (evidence_payload ->> 'recorded_at')::timestamptz;
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'document-record canonical evidence timestamps are invalid'
            USING ERRCODE = '22023';
    END;

    IF evidence_received_at IS DISTINCT FROM NEW.received_at
       OR evidence_recorded_at < evidence_received_at
       OR evidence_recorded_at > NEW.recorded_at THEN
        RAISE EXCEPTION 'document-record canonical evidence chronology does not match persistence time'
            USING ERRCODE = '23514';
    END IF;

    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION validate_document_record_evidence_binding() IS
    'After insert constraints and system-time checks, validates exact canonical DocumentRecordEvidence bytes, SHA-256 digest, schema/key shape, typed metadata equality, and evidence chronology without reading foreign application tables.';

CREATE TRIGGER document_record_evidence_binding_guard
AFTER INSERT ON document_record
FOR EACH ROW
EXECUTE FUNCTION validate_document_record_evidence_binding();

CREATE FUNCTION protect_document_record_immutability()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'document metadata is immutable; lifecycle changes require a separate governed relation'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION protect_document_record_immutability() IS
    'Rejects UPDATE and DELETE so the artifact/provenance metadata snapshot cannot be rewritten after issuance.';

CREATE TRIGGER document_record_immutability_guard
BEFORE UPDATE OR DELETE ON document_record
FOR EACH ROW
EXECUTE FUNCTION protect_document_record_immutability();

CREATE FUNCTION reject_document_record_truncate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'document-record history cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION reject_document_record_truncate() IS
    'Rejects table-wide TRUNCATE so immutable document metadata cannot bypass row-level controls.';

CREATE TRIGGER document_record_truncate_guard
BEFORE TRUNCATE ON document_record
FOR EACH STATEMENT
EXECUTE FUNCTION reject_document_record_truncate();

REVOKE TRUNCATE ON document_record FROM PUBLIC;

ALTER TABLE document_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_record FORCE ROW LEVEL SECURITY;

CREATE POLICY document_record_tenant_isolation_policy
ON document_record
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
