-- Reject owner-operation observations that claim knowledge from the future or are already stale.
-- Application validation performs the same check before persistence, but current production
-- PostgreSQL truth must enforce the temporal evidence boundary independently of caller code.
-- Existing future-dated history cannot be grandfathered into the stronger authority boundary.

DO $$
DECLARE
    wall_clock_unix_ms bigint;
BEGIN
    wall_clock_unix_ms := floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint;

    IF EXISTS (
        SELECT 1
        FROM public.product_composition_activation_owner_observation
        WHERE observed_at_unix_ms > wall_clock_unix_ms
    ) THEN
        RAISE EXCEPTION
            'product composition activation registry contains future-dated owner observation history';
    END IF;
END;
$$;

CREATE FUNCTION validate_product_composition_activation_observation_wall_clock()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
    wall_clock_unix_ms bigint;
BEGIN
    wall_clock_unix_ms := floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint;

    IF NEW.observed_at_unix_ms > wall_clock_unix_ms THEN
        RAISE EXCEPTION
            'product composition owner observation cannot be dated after database wall clock';
    END IF;

    IF NEW.valid_until_unix_ms <= wall_clock_unix_ms THEN
        RAISE EXCEPTION
            'product composition owner observation must be fresh when persisted';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER product_composition_activation_owner_observation_wall_clock_guard
BEFORE INSERT ON public.product_composition_activation_owner_observation
FOR EACH ROW
EXECUTE FUNCTION validate_product_composition_activation_observation_wall_clock();
