-- Preserve exact canonical DocumentRecordEvidence object semantics before jsonb
-- normalization can collapse duplicate object keys.

BEGIN;

SET LOCAL search_path = public, pg_catalog;

ALTER TABLE document_record
    ADD CONSTRAINT document_canonical_evidence_unique_keys_check
    CHECK (canonical_evidence_json IS JSON OBJECT WITH UNIQUE KEYS);

COMMENT ON CONSTRAINT document_canonical_evidence_unique_keys_check ON document_record IS
    'Rejects invalid, non-object, or duplicate-key canonical evidence before jsonb normalization; reviewed DocumentRecordEvidence bytes must represent one unique-key JSON object.';

COMMIT;
