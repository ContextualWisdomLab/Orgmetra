-- Record assignment role classification as authoritative HRIS truth.
-- Historical rows are preserved explicitly; no allocation/order heuristic is allowed.
-- legacy_unspecified is migration provenance only: the NOT VALID check preserves
-- pre-contract rows while enforcing primary/concurrent_secondary for every new
-- or subsequently rewritten row.

ALTER TABLE public.assignment_record
    ADD COLUMN assignment_category_code text;

UPDATE public.assignment_record
SET assignment_category_code = 'legacy_unspecified'
WHERE assignment_category_code IS NULL;

ALTER TABLE public.assignment_record
    ALTER COLUMN assignment_category_code SET NOT NULL;

ALTER TABLE public.assignment_record
    ADD CONSTRAINT assignment_record_category_code_check
    CHECK (assignment_category_code IN ('primary', 'concurrent_secondary')) NOT VALID;

ALTER TABLE public.assignment_record
    ADD CONSTRAINT assignment_record_primary_bitemporal_exclusion
    EXCLUDE USING gist (
        tenant_record_id WITH =,
        employment_record_id WITH =,
        daterange(effective_from, effective_to, '[)') WITH &&,
        tstzrange(recorded_from, recorded_to, '[)') WITH &&
    )
    WHERE (assignment_category_code = 'primary');
