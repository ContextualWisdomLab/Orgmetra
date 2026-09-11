-- Bind persisted evidence to the exact deterministic JSON encoding emitted by
-- DocumentRecordEvidence, not only to an arbitrary semantically equivalent JSON
-- representation whose digest was recomputed by the caller.

BEGIN;

SET LOCAL search_path = public, pg_catalog;

CREATE FUNCTION public.validate_document_record_canonical_encoding()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    evidence_payload jsonb;
    evidence_recorded_at timestamptz;
    canonical_received_at text;
    canonical_recorded_at text;
    expected_canonical_evidence text;
BEGIN
    -- Migration 0022 and the earlier evidence-binding trigger already establish
    -- one unique-key object, the exact v1 key set, typed-field equality, and
    -- timestamp validity before this same-event trigger runs.
    evidence_payload := NEW.canonical_evidence_json::jsonb;
    evidence_recorded_at := (evidence_payload ->> 'recorded_at')::timestamptz;

    canonical_received_at := pg_catalog.regexp_replace(
        pg_catalog.to_char(
            NEW.received_at AT TIME ZONE 'UTC',
            'YYYY-MM-DD"T"HH24:MI:SS.US'
        ),
        '\.000000$',
        ''
    ) || 'Z';
    canonical_recorded_at := pg_catalog.regexp_replace(
        pg_catalog.to_char(
            evidence_recorded_at AT TIME ZONE 'UTC',
            'YYYY-MM-DD"T"HH24:MI:SS.US'
        ),
        '\.000000$',
        ''
    ) || 'Z';

    -- Every v1 value is already constrained to ASCII-safe reviewed vocabularies,
    -- UUID references, lowercase digests, or canonical UTC timestamps. to_json()
    -- therefore supplies the same JSON string escaping contract while the fixed
    -- concatenation preserves Python json.dumps(sort_keys=True,
    -- separators=(",", ":"), ensure_ascii=True) key order and separators.
    expected_canonical_evidence :=
        '{' ||
        '"artifact_digest":' || pg_catalog.to_json(NEW.artifact_digest_sha256)::text || ',' ||
        '"artifact_reference":' || pg_catalog.to_json(NEW.artifact_reference)::text || ',' ||
        '"classification_code":' || pg_catalog.to_json(NEW.classification_code)::text || ',' ||
        '"content_storage_state":' || pg_catalog.to_json(NEW.content_storage_state)::text || ',' ||
        '"decision_authority_state":' || pg_catalog.to_json(NEW.decision_authority_state)::text || ',' ||
        '"document_category_code":' || pg_catalog.to_json(NEW.document_category_code)::text || ',' ||
        '"document_record_reference":' || pg_catalog.to_json(NEW.document_record_reference)::text || ',' ||
        '"employment_record_reference":' || pg_catalog.to_json(NEW.employment_record_reference)::text || ',' ||
        '"person_record_reference":' || pg_catalog.to_json(NEW.person_record_reference)::text || ',' ||
        '"received_at":' || pg_catalog.to_json(canonical_received_at)::text || ',' ||
        '"recorded_at":' || pg_catalog.to_json(canonical_recorded_at)::text || ',' ||
        '"retention_policy_digest":' || pg_catalog.to_json(NEW.retention_policy_digest_sha256)::text || ',' ||
        '"retention_policy_reference":' || pg_catalog.to_json(NEW.retention_policy_reference)::text || ',' ||
        '"schema_version":' || pg_catalog.to_json('orgmetra.document_record_evidence.v1'::text)::text || ',' ||
        '"source_provenance_digest":' || pg_catalog.to_json(NEW.source_provenance_digest_sha256)::text || ',' ||
        '"tenant_record_id":' || pg_catalog.to_json(NEW.tenant_record_id::text)::text || ',' ||
        '"uploader_actor_reference":' || pg_catalog.to_json(NEW.uploader_actor_reference)::text ||
        '}';

    IF NEW.canonical_evidence_json IS DISTINCT FROM expected_canonical_evidence THEN
        RAISE EXCEPTION 'document-record canonical evidence bytes are not the deterministic v1 encoding'
            USING ERRCODE = '23514';
    END IF;

    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION public.validate_document_record_canonical_encoding() IS
    'Rejects alternate whitespace, key-order, timestamp-text, or other semantically equivalent JSON representations; durable evidence must equal the deterministic v1 canonical bytes emitted by DocumentRecordEvidence.';

CREATE TRIGGER document_record_z_canonical_encoding_guard
AFTER INSERT ON document_record
FOR EACH ROW
EXECUTE FUNCTION public.validate_document_record_canonical_encoding();

COMMIT;
