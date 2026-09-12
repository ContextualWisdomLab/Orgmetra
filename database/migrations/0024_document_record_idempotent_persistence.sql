-- Bind one purpose-scoped idempotency key to one semantic document persistence
-- command and its first committed result. The advisory lock covers only the
-- database transaction that checks replay state and writes the immutable fact;
-- no external computation or network work occurs while it is held.

-- Capability-role names are security boundaries. Reusing an existing cluster
-- role could retain memberships or object ACLs that CREATE ROLE cannot erase.
-- Fail before changing any project object so a collision cannot leave partial
-- persistence migration state behind.
DO $orgmetra_document_persistence_role_preflight$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_catalog.pg_roles
        WHERE rolname IN (
            'orgmetra_document_persistence_owner',
            'orgmetra_document_persistence_executor'
        )
    ) THEN
        RAISE EXCEPTION 'pre-existing document persistence capability role is not accepted'
            USING ERRCODE = '42710';
    END IF;
END;
$orgmetra_document_persistence_role_preflight$;

BEGIN;

SET LOCAL search_path = public, pg_catalog;

ALTER TABLE document_record
    ADD CONSTRAINT document_record_tenant_identity_unique
    UNIQUE (tenant_record_id, document_record_id);

CREATE TABLE document_record_persist_receipt (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    idempotency_key text NOT NULL,
    semantic_command_digest_sha256 text NOT NULL,
    document_record_id uuid NOT NULL,
    receipt_digest_sha256 text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),

    CONSTRAINT document_record_persist_idempotency_key_check
        CHECK (
            idempotency_key ~
            '^document-record-persist-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT document_record_persist_semantic_digest_check
        CHECK (semantic_command_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT document_record_persist_receipt_digest_check
        CHECK (receipt_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT document_record_persist_receipt_command_unique
        UNIQUE (tenant_record_id, idempotency_key),
    CONSTRAINT document_record_persist_receipt_document_unique
        UNIQUE (tenant_record_id, document_record_id),
    CONSTRAINT document_record_persist_receipt_document_fk
        FOREIGN KEY (tenant_record_id, document_record_id)
        REFERENCES document_record(tenant_record_id, document_record_id)
);

COMMENT ON TABLE document_record_persist_receipt IS
    'Append-only, tenant-scoped replay receipt for document_records persistence. It stores only an opaque purpose-bound key, semantic command digest, committed document identity, and receipt digest; document bytes and free-form HR content are excluded.';

CREATE TRIGGER document_record_persist_receipt_append_only_guard
BEFORE UPDATE OR DELETE ON document_record_persist_receipt
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

CREATE FUNCTION public.reject_document_record_persist_receipt_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'document-record persistence receipts are append-only and cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER document_record_persist_receipt_truncate_guard
BEFORE TRUNCATE ON document_record_persist_receipt
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_document_record_persist_receipt_truncate();

REVOKE TRUNCATE ON document_record_persist_receipt FROM PUBLIC;

ALTER TABLE document_record_persist_receipt ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_record_persist_receipt FORCE ROW LEVEL SECURITY;

CREATE POLICY document_record_persist_receipt_tenant_policy
ON document_record_persist_receipt
USING (tenant_record_id = public.current_tenant_record_id())
WITH CHECK (tenant_record_id = public.current_tenant_record_id());

CREATE FUNCTION public.persist_document_record_once(
    p_tenant_record_id uuid,
    p_idempotency_key text,
    p_document_record_id uuid,
    p_document_record_reference text,
    p_person_record_reference text,
    p_employment_record_reference text,
    p_uploader_actor_reference text,
    p_persisted_by_actor_reference text,
    p_document_category_code text,
    p_artifact_reference text,
    p_artifact_digest_sha256 text,
    p_source_provenance_digest_sha256 text,
    p_retention_policy_reference text,
    p_retention_policy_digest_sha256 text,
    p_received_at timestamptz,
    p_canonical_evidence_json text,
    p_evidence_digest_sha256 text,
    p_audit_event_reference text,
    p_outbox_event_reference text,
    p_application_evidence_digest_sha256 text
)
RETURNS TABLE (
    document_record_id uuid,
    document_record_reference text,
    audit_event_reference text,
    outbox_event_reference text,
    semantic_command_digest_sha256 text,
    receipt_digest_sha256 text,
    recorded_at timestamptz
)
LANGUAGE plpgsql
VOLATILE
SET search_path = pg_catalog, public, pg_temp
SET TimeZone = 'UTC'
AS $$
DECLARE
    v_semantic_command_digest text;
    v_existing_semantic_digest text;
    v_document_recorded_at timestamptz;
    v_receipt_digest text;
BEGIN
    IF pg_catalog.current_setting('transaction_isolation') IS DISTINCT FROM 'read committed' THEN
        RAISE EXCEPTION 'document persistence idempotency requires read committed transaction isolation'
            USING ERRCODE = '25000';
    END IF;

    IF p_tenant_record_id IS NULL
       OR p_idempotency_key IS NULL
       OR p_document_record_id IS NULL
       OR p_document_record_reference IS NULL
       OR p_person_record_reference IS NULL
       OR p_employment_record_reference IS NULL
       OR p_uploader_actor_reference IS NULL
       OR p_persisted_by_actor_reference IS NULL
       OR p_document_category_code IS NULL
       OR p_artifact_reference IS NULL
       OR p_artifact_digest_sha256 IS NULL
       OR p_source_provenance_digest_sha256 IS NULL
       OR p_retention_policy_reference IS NULL
       OR p_retention_policy_digest_sha256 IS NULL
       OR p_received_at IS NULL
       OR p_canonical_evidence_json IS NULL
       OR p_evidence_digest_sha256 IS NULL
       OR p_audit_event_reference IS NULL
       OR p_outbox_event_reference IS NULL
       OR p_application_evidence_digest_sha256 IS NULL THEN
        RAISE EXCEPTION 'document persistence command cannot contain null authoritative fields'
            USING ERRCODE = '22004';
    END IF;

    IF public.current_tenant_record_id() IS DISTINCT FROM p_tenant_record_id THEN
        RAISE EXCEPTION 'document persistence tenant context does not match requested tenant'
            USING ERRCODE = '42501';
    END IF;

    IF p_idempotency_key !~
       '^document-record-persist-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' THEN
        RAISE EXCEPTION 'document persistence idempotency key must be one opaque purpose-bound UUID reference'
            USING ERRCODE = '22023';
    END IF;

    v_semantic_command_digest := pg_catalog.encode(
        public.digest(
            pg_catalog.convert_to(
                pg_catalog.jsonb_build_object(
                    'schema_version', 'orgmetra.document_record_persist_command.v1',
                    'tenant_record_id', p_tenant_record_id::text,
                    'document_record_id', p_document_record_id::text,
                    'document_record_reference', p_document_record_reference,
                    'person_record_reference', p_person_record_reference,
                    'employment_record_reference', p_employment_record_reference,
                    'uploader_actor_reference', p_uploader_actor_reference,
                    'persisted_by_actor_reference', p_persisted_by_actor_reference,
                    'document_category_code', p_document_category_code,
                    'artifact_reference', p_artifact_reference,
                    'artifact_digest_sha256', p_artifact_digest_sha256,
                    'source_provenance_digest_sha256', p_source_provenance_digest_sha256,
                    'retention_policy_reference', p_retention_policy_reference,
                    'retention_policy_digest_sha256', p_retention_policy_digest_sha256,
                    'received_at', p_received_at,
                    'canonical_evidence_json', p_canonical_evidence_json,
                    'evidence_digest_sha256', p_evidence_digest_sha256,
                    'audit_event_reference', p_audit_event_reference,
                    'outbox_event_reference', p_outbox_event_reference,
                    'application_evidence_digest_sha256', p_application_evidence_digest_sha256,
                    'application_purpose_code', 'document_record_persist',
                    'application_reason_code', 'reviewed_document_metadata'
                )::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    -- Match the established People mutation pattern: hold a transaction-scoped
    -- key lock only around replay lookup plus the authoritative database write.
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(
            p_tenant_record_id::text || E'\\x1fdocument_records\\x1f' || p_idempotency_key,
            0
        )
    );

    SELECT receipt.semantic_command_digest_sha256
    INTO v_existing_semantic_digest
    FROM public.document_record_persist_receipt AS receipt
    WHERE receipt.tenant_record_id = p_tenant_record_id
      AND receipt.idempotency_key = p_idempotency_key;

    IF FOUND THEN
        IF v_existing_semantic_digest IS DISTINCT FROM v_semantic_command_digest THEN
            RAISE EXCEPTION 'idempotency key is bound to a different document persistence command'
                USING ERRCODE = '23514';
        END IF;

        RETURN QUERY
        SELECT
            persisted.document_record_id,
            persisted.document_record_reference,
            persisted.audit_event_reference,
            persisted.outbox_event_reference,
            receipt.semantic_command_digest_sha256,
            receipt.receipt_digest_sha256,
            persisted.recorded_at
        FROM public.document_record_persist_receipt AS receipt
        JOIN public.document_record AS persisted
          ON persisted.tenant_record_id = receipt.tenant_record_id
         AND persisted.document_record_id = receipt.document_record_id
        WHERE receipt.tenant_record_id = p_tenant_record_id
          AND receipt.idempotency_key = p_idempotency_key;
        RETURN;
    END IF;

    INSERT INTO public.document_record (
        tenant_record_id,
        document_record_id,
        document_record_reference,
        person_record_reference,
        employment_record_reference,
        uploader_actor_reference,
        persisted_by_actor_reference,
        document_category_code,
        artifact_reference,
        artifact_digest_sha256,
        source_provenance_digest_sha256,
        retention_policy_reference,
        retention_policy_digest_sha256,
        received_at,
        canonical_evidence_json,
        evidence_digest_sha256,
        audit_event_reference,
        outbox_event_reference,
        application_evidence_digest_sha256,
        application_purpose_code,
        application_reason_code
    ) VALUES (
        p_tenant_record_id,
        p_document_record_id,
        p_document_record_reference,
        p_person_record_reference,
        p_employment_record_reference,
        p_uploader_actor_reference,
        p_persisted_by_actor_reference,
        p_document_category_code,
        p_artifact_reference,
        p_artifact_digest_sha256,
        p_source_provenance_digest_sha256,
        p_retention_policy_reference,
        p_retention_policy_digest_sha256,
        p_received_at,
        p_canonical_evidence_json,
        p_evidence_digest_sha256,
        p_audit_event_reference,
        p_outbox_event_reference,
        p_application_evidence_digest_sha256,
        'document_record_persist',
        'reviewed_document_metadata'
    )
    RETURNING document_record.recorded_at INTO v_document_recorded_at;

    v_receipt_digest := pg_catalog.encode(
        public.digest(
            pg_catalog.convert_to(
                pg_catalog.jsonb_build_object(
                    'schema_version', 'orgmetra.document_record_persist_receipt.v1',
                    'tenant_record_id', p_tenant_record_id::text,
                    'idempotency_key', p_idempotency_key,
                    'semantic_command_digest_sha256', v_semantic_command_digest,
                    'document_record_id', p_document_record_id::text,
                    'document_record_reference', p_document_record_reference,
                    'audit_event_reference', p_audit_event_reference,
                    'outbox_event_reference', p_outbox_event_reference,
                    'document_recorded_at', v_document_recorded_at
                )::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    INSERT INTO public.document_record_persist_receipt (
        tenant_record_id,
        idempotency_key,
        semantic_command_digest_sha256,
        document_record_id,
        receipt_digest_sha256,
        recorded_at
    ) VALUES (
        p_tenant_record_id,
        p_idempotency_key,
        v_semantic_command_digest,
        p_document_record_id,
        v_receipt_digest,
        v_document_recorded_at
    );

    RETURN QUERY
    SELECT
        p_document_record_id,
        p_document_record_reference,
        p_audit_event_reference,
        p_outbox_event_reference,
        v_semantic_command_digest,
        v_receipt_digest,
        v_document_recorded_at;
END;
$$;

-- PostgreSQL grants EXECUTE on newly created functions to PUBLIC by default.
-- Revoke that ambient capability before transferring this write boundary to a
-- dedicated NOLOGIN owner. The externally assignable executor gets only
-- schema USAGE + function EXECUTE and therefore cannot bypass replay semantics
-- through direct table DML.
REVOKE EXECUTE ON FUNCTION public.persist_document_record_once(
    uuid, text, uuid, text, text, text, text, text, text, text, text, text,
    text, text, timestamptz, text, text, text, text, text
) FROM PUBLIC;

CREATE ROLE orgmetra_document_persistence_owner
    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE orgmetra_document_persistence_executor
    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

GRANT USAGE ON SCHEMA public
    TO orgmetra_document_persistence_owner, orgmetra_document_persistence_executor;
GRANT SELECT, INSERT ON TABLE public.document_record
    TO orgmetra_document_persistence_owner;
GRANT SELECT, INSERT ON TABLE public.document_record_persist_receipt
    TO orgmetra_document_persistence_owner;
GRANT EXECUTE ON FUNCTION public.current_tenant_record_id()
    TO orgmetra_document_persistence_owner;
GRANT EXECUTE ON FUNCTION public.digest(bytea, text)
    TO orgmetra_document_persistence_owner;

-- ALTER FUNCTION OWNER requires CREATE on the containing schema for the target
-- owner. Grant it only for this ownership handoff, then revoke it before commit.
GRANT CREATE ON SCHEMA public TO orgmetra_document_persistence_owner;
ALTER FUNCTION public.persist_document_record_once(
    uuid, text, uuid, text, text, text, text, text, text, text, text, text,
    text, text, timestamptz, text, text, text, text, text
) OWNER TO orgmetra_document_persistence_owner;
ALTER FUNCTION public.persist_document_record_once(
    uuid, text, uuid, text, text, text, text, text, text, text, text, text,
    text, text, timestamptz, text, text, text, text, text
) SECURITY DEFINER;
REVOKE CREATE ON SCHEMA public FROM orgmetra_document_persistence_owner;
GRANT EXECUTE ON FUNCTION public.persist_document_record_once(
    uuid, text, uuid, text, text, text, text, text, text, text, text, text,
    text, text, timestamptz, text, text, text, text, text
) TO orgmetra_document_persistence_executor;

COMMENT ON FUNCTION public.persist_document_record_once(
    uuid, text, uuid, text, text, text, text, text, text, text, text, text,
    text, text, timestamptz, text, text, text, text, text
) IS
    'Persists one immutable document-record fact and replay receipt under a tenant-scoped transaction advisory lock. The SECURITY DEFINER function is owned by a dedicated NOLOGIN/NOBYPASSRLS role with only SELECT/INSERT on document persistence tables; the externally assignable executor role has EXECUTE only and cannot bypass replay semantics with direct DML. The caller tenant context must match the requested tenant before any replay lock or durable write. The owner fails closed outside Read Committed because replay visibility relies on a fresh post-lock statement snapshot. Same-key same-semantic retries return the first committed result; changed semantics fail closed. Digest serialization uses function-local UTC so equivalent timestamptz values do not change replay identity across caller sessions.';

COMMIT;
