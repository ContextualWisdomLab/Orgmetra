-- Bind durable Employment work-capacity truth to the one canonical JSON byte
-- representation issued by the governed parent review packet. A caller must not be
-- able to reorder keys or add semantically irrelevant whitespace, recompute SHA-256,
-- and create a second durable representation of the same reviewed evidence.

CREATE FUNCTION enforce_employment_work_capacity_canonical_review_evidence()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    review_payload jsonb;
    canonical_review_json text;
BEGIN
    BEGIN
        review_payload := NEW.review_evidence_json::jsonb;
    EXCEPTION WHEN others THEN
        RAISE EXCEPTION 'review evidence must be valid JSON'
            USING ERRCODE = '22023';
    END;

    IF pg_catalog.jsonb_typeof(review_payload) <> 'object' THEN
        RAISE EXCEPTION 'review evidence must be one JSON object'
            USING ERRCODE = '22023';
    END IF;

    SELECT '{' || pg_catalog.string_agg(
        pg_catalog.to_json(review_key)::text || ':' || review_value::text,
        ',' ORDER BY review_key COLLATE "C"
    ) || '}'
    INTO canonical_review_json
    FROM pg_catalog.jsonb_each(review_payload) AS item(review_key, review_value);

    IF NEW.review_evidence_json IS DISTINCT FROM canonical_review_json THEN
        RAISE EXCEPTION 'review evidence must use exact canonical JSON bytes'
            USING ERRCODE = '22023';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION enforce_employment_work_capacity_canonical_review_evidence() IS
    'Requires the exact compact, C-key-sorted JSON representation emitted by EmploymentWorkCapacityReviewPacket before durable work-capacity persistence.';

CREATE TRIGGER employment_work_capacity_canonical_review_guard
BEFORE INSERT ON employment_work_capacity_version
FOR EACH ROW
EXECUTE FUNCTION enforce_employment_work_capacity_canonical_review_evidence();

REVOKE ALL ON FUNCTION enforce_employment_work_capacity_canonical_review_evidence() FROM PUBLIC;
