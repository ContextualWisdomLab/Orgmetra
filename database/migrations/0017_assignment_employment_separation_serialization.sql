-- Serialize Assignment creation against Employment separation on the Employment aggregate.
--
-- Separation already locks employment_record before it inspects Assignment truth. Assignment
-- creation must acquire the same anchor lock before INSERT and then re-read current Employment
-- versions under READ COMMITTED. This closes the check/insert race in both directions without
-- holding an external workflow or broad table lock inside the transaction.

BEGIN;

SET LOCAL search_path = public, pg_catalog;

CREATE FUNCTION public.guard_assignment_employment_coverage()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    v_anchor_person_id uuid;
    v_has_covering_employment boolean;
BEGIN
    SELECT employment.person_record_id
    INTO v_anchor_person_id
    FROM public.employment_record AS employment
    WHERE employment.tenant_record_id = NEW.tenant_record_id
      AND employment.employment_record_id = NEW.employment_record_id
    FOR UPDATE OF employment;

    IF NOT FOUND OR v_anchor_person_id IS DISTINCT FROM NEW.person_record_id THEN
        RAISE EXCEPTION 'assignment target does not match tenant person and employment'
            USING ERRCODE = '23503';
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM public.employment_record_version AS version
        WHERE version.tenant_record_id = NEW.tenant_record_id
          AND version.employment_record_id = NEW.employment_record_id
          AND version.recorded_to IS NULL
          AND version.employment_status_code IN ('active', 'leave')
          AND version.effective_from <= NEW.effective_from
          AND (
                version.effective_to IS NULL
                OR (
                    NEW.effective_to IS NOT NULL
                    AND NEW.effective_to <= version.effective_to
                )
          )
    )
    INTO v_has_covering_employment;

    IF v_has_covering_employment IS NOT TRUE THEN
        RAISE EXCEPTION 'assignment requires current active or leave Employment coverage'
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER assignment_employment_coverage_guard
BEFORE INSERT ON public.assignment_record
FOR EACH ROW
EXECUTE FUNCTION public.guard_assignment_employment_coverage();

COMMIT;
