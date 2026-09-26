BEGIN;

-- Trigger-function identity is part of durable activation authority. Earlier migrations set a
-- safe runtime search_path inside each function, but several CREATE TRIGGER statements resolved
-- function names through the migration session search_path. Fence all durable writer relations,
-- require the canonical public functions to be owned by the same role as the deployment table,
-- then rebind every activation/recovery trigger through an explicit public-qualified function.
LOCK TABLE
    public.product_composition_deployment,
    public.product_composition_activation_evidence,
    public.product_composition_activation_owner_observation,
    public.product_composition_activation_event,
    public.product_composition_recovery_attestation
IN SHARE ROW EXCLUSIVE MODE;

DO $provenance$
DECLARE
    expected_owner oid;
    function_name text;
    function_oid oid;
    function_owner oid;
BEGIN
    SELECT relation.relowner
    INTO expected_owner
    FROM pg_catalog.pg_class AS relation
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = relation.relnamespace
    WHERE namespace.nspname = 'public'
      AND relation.relname = 'product_composition_deployment'
      AND relation.relkind = 'r';

    IF expected_owner IS NULL THEN
        RAISE EXCEPTION 'product composition deployment authority relation is missing';
    END IF;

    FOREACH function_name IN ARRAY ARRAY[
        'lock_product_composition_deployment_write',
        'validate_product_composition_activation_observation_insert',
        'validate_product_composition_activation_observation_wall_clock',
        'validate_product_composition_activation_insert',
        'validate_product_composition_recovery_attestation_insert',
        'reject_append_only_mutation',
        'reject_product_composition_activation_registry_truncate'
    ]
    LOOP
        function_oid := pg_catalog.to_regprocedure(
            pg_catalog.format('public.%I()', function_name)
        );

        IF function_oid IS NULL THEN
            RAISE EXCEPTION 'required public trigger function %() is missing', function_name;
        END IF;

        SELECT function_definition.proowner
        INTO function_owner
        FROM pg_catalog.pg_proc AS function_definition
        WHERE function_definition.oid = function_oid;

        IF function_owner IS DISTINCT FROM expected_owner THEN
            RAISE EXCEPTION
                'required public trigger function %() is not owned by deployment authority owner',
                function_name;
        END IF;
    END LOOP;
END;
$provenance$;

DROP TRIGGER IF EXISTS product_composition_activation_event_00_deployment_lock_guard
    ON public.product_composition_activation_event;
CREATE TRIGGER product_composition_activation_event_00_deployment_lock_guard
BEFORE INSERT ON public.product_composition_activation_event
FOR EACH ROW
EXECUTE FUNCTION public.lock_product_composition_deployment_write();

DROP TRIGGER IF EXISTS product_composition_activation_event_lineage_guard
    ON public.product_composition_activation_event;
CREATE TRIGGER product_composition_activation_event_lineage_guard
BEFORE INSERT ON public.product_composition_activation_event
FOR EACH ROW
EXECUTE FUNCTION public.validate_product_composition_activation_insert();

DROP TRIGGER IF EXISTS product_composition_recovery_attestation_00_deployment_lock_guard
    ON public.product_composition_recovery_attestation;
CREATE TRIGGER product_composition_recovery_attestation_00_deployment_lock_guard
BEFORE INSERT ON public.product_composition_recovery_attestation
FOR EACH ROW
EXECUTE FUNCTION public.lock_product_composition_deployment_write();

DROP TRIGGER IF EXISTS product_composition_recovery_attestation_insert_guard
    ON public.product_composition_recovery_attestation;
CREATE TRIGGER product_composition_recovery_attestation_insert_guard
BEFORE INSERT ON public.product_composition_recovery_attestation
FOR EACH ROW
EXECUTE FUNCTION public.validate_product_composition_recovery_attestation_insert();

DROP TRIGGER IF EXISTS product_composition_activation_owner_observation_insert_guard
    ON public.product_composition_activation_owner_observation;
CREATE TRIGGER product_composition_activation_owner_observation_insert_guard
BEFORE INSERT ON public.product_composition_activation_owner_observation
FOR EACH ROW
EXECUTE FUNCTION public.validate_product_composition_activation_observation_insert();

DROP TRIGGER IF EXISTS product_composition_activation_owner_observation_wall_clock_guard
    ON public.product_composition_activation_owner_observation;
CREATE TRIGGER product_composition_activation_owner_observation_wall_clock_guard
BEFORE INSERT ON public.product_composition_activation_owner_observation
FOR EACH ROW
EXECUTE FUNCTION public.validate_product_composition_activation_observation_wall_clock();

DROP TRIGGER IF EXISTS product_composition_deployment_append_only_guard
    ON public.product_composition_deployment;
CREATE TRIGGER product_composition_deployment_append_only_guard
BEFORE UPDATE OR DELETE ON public.product_composition_deployment
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

DROP TRIGGER IF EXISTS product_composition_activation_evidence_append_only_guard
    ON public.product_composition_activation_evidence;
CREATE TRIGGER product_composition_activation_evidence_append_only_guard
BEFORE UPDATE OR DELETE ON public.product_composition_activation_evidence
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

DROP TRIGGER IF EXISTS product_composition_activation_owner_observation_append_only_guard
    ON public.product_composition_activation_owner_observation;
CREATE TRIGGER product_composition_activation_owner_observation_append_only_guard
BEFORE UPDATE OR DELETE ON public.product_composition_activation_owner_observation
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

DROP TRIGGER IF EXISTS product_composition_activation_event_append_only_guard
    ON public.product_composition_activation_event;
CREATE TRIGGER product_composition_activation_event_append_only_guard
BEFORE UPDATE OR DELETE ON public.product_composition_activation_event
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

DROP TRIGGER IF EXISTS product_composition_recovery_attestation_append_only_guard
    ON public.product_composition_recovery_attestation;
CREATE TRIGGER product_composition_recovery_attestation_append_only_guard
BEFORE UPDATE OR DELETE ON public.product_composition_recovery_attestation
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

DROP TRIGGER IF EXISTS product_composition_deployment_truncate_guard
    ON public.product_composition_deployment;
CREATE TRIGGER product_composition_deployment_truncate_guard
BEFORE TRUNCATE ON public.product_composition_deployment
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_product_composition_activation_registry_truncate();

DROP TRIGGER IF EXISTS product_composition_activation_evidence_truncate_guard
    ON public.product_composition_activation_evidence;
CREATE TRIGGER product_composition_activation_evidence_truncate_guard
BEFORE TRUNCATE ON public.product_composition_activation_evidence
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_product_composition_activation_registry_truncate();

DROP TRIGGER IF EXISTS product_composition_activation_owner_observation_truncate_guard
    ON public.product_composition_activation_owner_observation;
CREATE TRIGGER product_composition_activation_owner_observation_truncate_guard
BEFORE TRUNCATE ON public.product_composition_activation_owner_observation
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_product_composition_activation_registry_truncate();

DROP TRIGGER IF EXISTS product_composition_activation_event_truncate_guard
    ON public.product_composition_activation_event;
CREATE TRIGGER product_composition_activation_event_truncate_guard
BEFORE TRUNCATE ON public.product_composition_activation_event
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_product_composition_activation_registry_truncate();

DROP TRIGGER IF EXISTS product_composition_recovery_attestation_truncate_guard
    ON public.product_composition_recovery_attestation;
CREATE TRIGGER product_composition_recovery_attestation_truncate_guard
BEFORE TRUNCATE ON public.product_composition_recovery_attestation
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_product_composition_activation_registry_truncate();

COMMIT;
