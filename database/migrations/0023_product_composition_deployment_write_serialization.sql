BEGIN;

-- Activation and restart-recovery are one deployment-state authority. Application adapters
-- already serialize both operations by locking product_composition_deployment, but direct
-- SQL must not be able to bypass that ordering. Drain predecessor direct writers before
-- publishing database-enforced lock guards, then make both INSERT paths acquire the same
-- deployment row lock before their existing lineage/evidence validation triggers run.
LOCK TABLE public.product_composition_activation_event IN SHARE ROW EXCLUSIVE MODE;
LOCK TABLE public.product_composition_recovery_attestation IN SHARE ROW EXCLUSIVE MODE;

CREATE FUNCTION lock_product_composition_deployment_write()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    PERFORM 1
    FROM public.product_composition_deployment
    WHERE deployment_id = NEW.deployment_id
      AND environment_id = NEW.environment_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'product composition deployment does not exist';
    END IF;

    RETURN NEW;
END;
$$;

-- PostgreSQL runs triggers of the same timing/event in name order. The `00` names therefore
-- acquire the shared deployment lock before the pre-existing lineage/evidence guards inspect
-- current activation or recovery state.
CREATE TRIGGER product_composition_activation_event_00_deployment_lock_guard
BEFORE INSERT ON public.product_composition_activation_event
FOR EACH ROW
EXECUTE FUNCTION lock_product_composition_deployment_write();

CREATE TRIGGER product_composition_recovery_attestation_00_deployment_lock_guard
BEFORE INSERT ON public.product_composition_recovery_attestation
FOR EACH ROW
EXECUTE FUNCTION lock_product_composition_deployment_write();

COMMIT;
