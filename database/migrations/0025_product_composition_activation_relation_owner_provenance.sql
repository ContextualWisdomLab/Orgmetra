BEGIN;
SET LOCAL search_path = pg_catalog, public;

-- Durable activation authority is split across several append-only relations. A
-- relation owner can alter or destroy that relation independently of ordinary
-- grants, including changing its trigger enforcement. The immutable generation
-- registry is the parent durable composition authority, so activation/recovery
-- relations must retain that same owner rather than merely agreeing with each
-- other. Fail closed on drift instead of silently reassigning ownership.
LOCK TABLE
    public.product_composition_generation,
    public.product_composition_deployment,
    public.product_composition_activation_evidence,
    public.product_composition_activation_owner_observation,
    public.product_composition_activation_event,
    public.product_composition_recovery_attestation
IN SHARE ROW EXCLUSIVE MODE;

DO $relation_owner_provenance$
DECLARE
    expected_owner oid;
    relation_name text;
    relation_owner oid;
BEGIN
    SELECT relation.relowner
    INTO expected_owner
    FROM pg_catalog.pg_class AS relation
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = relation.relnamespace
    WHERE namespace.nspname = 'public'
      AND relation.relname = 'product_composition_generation'
      AND relation.relkind = 'r';

    IF expected_owner IS NULL THEN
        RAISE EXCEPTION 'product composition generation authority relation is missing';
    END IF;

    FOREACH relation_name IN ARRAY ARRAY[
        'product_composition_deployment',
        'product_composition_activation_evidence',
        'product_composition_activation_owner_observation',
        'product_composition_activation_event',
        'product_composition_recovery_attestation'
    ]
    LOOP
        relation_owner := NULL;
        SELECT relation.relowner
        INTO relation_owner
        FROM pg_catalog.pg_class AS relation
        JOIN pg_catalog.pg_namespace AS namespace
          ON namespace.oid = relation.relnamespace
        WHERE namespace.nspname = 'public'
          AND relation.relname = relation_name
          AND relation.relkind = 'r';

        IF relation_owner IS NULL THEN
            RAISE EXCEPTION 'required public activation authority relation % is missing', relation_name;
        END IF;

        IF relation_owner IS DISTINCT FROM expected_owner THEN
            RAISE EXCEPTION
                'required public activation authority relation % is not owned by generation authority owner',
                relation_name;
        END IF;
    END LOOP;
END;
$relation_owner_provenance$;

COMMIT;
