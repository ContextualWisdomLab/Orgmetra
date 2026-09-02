-- Record assignment role classification as authoritative HRIS truth.
-- Historical rows are preserved explicitly; no allocation/order heuristic is allowed.
-- legacy_unspecified is migration provenance only. The table constraint preserves
-- that historical sentinel so system-time closure remains possible, while the
-- write guard rejects introduction of the sentinel on a new row or by changing
-- an already classified row back to legacy state.

ALTER TABLE public.assignment_record
    ADD COLUMN assignment_category_code text;

UPDATE public.assignment_record
SET assignment_category_code = 'legacy_unspecified'
WHERE assignment_category_code IS NULL;

ALTER TABLE public.assignment_record
    ALTER COLUMN assignment_category_code SET NOT NULL;

ALTER TABLE public.assignment_record
    ADD CONSTRAINT assignment_record_category_code_check
    CHECK (assignment_category_code IN ('legacy_unspecified', 'primary', 'concurrent_secondary')) NOT VALID;

CREATE FUNCTION public.enforce_assignment_category_write()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NEW.assignment_category_code = 'legacy_unspecified' THEN
        IF TG_OP = 'INSERT' THEN
            RAISE EXCEPTION 'assignment_record_category_code_check: legacy_unspecified is migration provenance only'
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'assignment_record_category_code_check',
                      TABLE = 'assignment_record',
                      SCHEMA = 'public';
        ELSIF OLD.assignment_category_code IS DISTINCT FROM 'legacy_unspecified' THEN
            RAISE EXCEPTION 'assignment_record_category_code_check: classified assignment cannot become legacy_unspecified'
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'assignment_record_category_code_check',
                      TABLE = 'assignment_record',
                      SCHEMA = 'public';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.enforce_assignment_category_write() IS
    'Rejects new or retroactively introduced legacy_unspecified assignment categories while preserving pre-contract system-time history.';

CREATE TRIGGER assignment_record_category_write_guard
BEFORE INSERT OR UPDATE OF assignment_category_code ON public.assignment_record
FOR EACH ROW
EXECUTE FUNCTION public.enforce_assignment_category_write();

COMMENT ON TRIGGER assignment_record_category_write_guard ON public.assignment_record IS
    'Keeps legacy_unspecified as migration provenance instead of a writable assignment classification.';

ALTER TABLE public.assignment_record
    ADD CONSTRAINT assignment_record_primary_bitemporal_exclusion
    EXCLUDE USING gist (
        tenant_record_id WITH =,
        employment_record_id WITH =,
        daterange(effective_from, effective_to, '[)') WITH &&,
        tstzrange(recorded_from, recorded_to, '[)') WITH &&
    )
    WHERE (assignment_category_code = 'primary');
