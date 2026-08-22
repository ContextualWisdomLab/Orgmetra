-- Prevent callers from authoring candidate-to-worker system-recorded time.
--
-- candidate_worker_conversion_record.recorded_from is knowledge/system time,
-- not business-effective time. Fresh inserts therefore use the PostgreSQL
-- transaction timestamp chosen by the authoritative persistence boundary.
-- effective_from remains independently caller-supplied business time and the
-- existing governance trigger continues to bind it to the confirmed decision.

BEGIN;

SET LOCAL search_path = public, pg_catalog;

CREATE FUNCTION public.enforce_candidate_conversion_system_recorded_time()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    IF NEW.recorded_from IS DISTINCT FROM pg_catalog.transaction_timestamp() THEN
        RAISE EXCEPTION 'candidate worker conversion recorded_from must equal system transaction time'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

-- PostgreSQL executes same-kind triggers in name order. The `a_` segment makes
-- system-time provenance fail closed before the broader conversion-governance
-- trigger performs foreign-key/evidence lookups.
CREATE TRIGGER candidate_conversion_a_system_recorded_time_guard
BEFORE INSERT ON public.candidate_worker_conversion_record
FOR EACH ROW
EXECUTE FUNCTION public.enforce_candidate_conversion_system_recorded_time();

COMMIT;
