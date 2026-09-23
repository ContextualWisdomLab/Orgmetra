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

-- Admission and durable generation authority preserve required=False routes as
-- optional. Activation and recovery therefore require every operation for a
-- required route, allow a wholly unobserved optional route, and fail closed
-- when any optional route is only partially observed. Replacing the existing
-- trigger functions keeps their trusted public identities and 0024 bindings.
CREATE OR REPLACE FUNCTION public.validate_product_composition_activation_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
    latest_sequence bigint;
    latest_generation_id text;
    evidence_valid_until_unix_ms bigint;
    evidence_authorization_action text;
    evidence_authorized_state_sequence bigint;
    wall_clock_unix_ms bigint;
BEGIN
    SELECT activation_sequence, generation_id
    INTO latest_sequence, latest_generation_id
    FROM public.product_composition_activation_event
    WHERE deployment_id = NEW.deployment_id
      AND environment_id = NEW.environment_id
    ORDER BY activation_sequence DESC
    LIMIT 1;

    IF latest_sequence IS NULL THEN
        IF NEW.activation_sequence <> 1
           OR NEW.previous_generation_id IS NOT NULL
           OR NEW.event_kind <> 'activate' THEN
            RAISE EXCEPTION 'first product composition activation must be sequence 1 activate with no previous generation';
        END IF;
    ELSE
        IF NEW.activation_sequence <> latest_sequence + 1 THEN
            RAISE EXCEPTION 'product composition activation sequence must advance exactly by one';
        END IF;

        IF NEW.previous_generation_id IS DISTINCT FROM latest_generation_id THEN
            RAISE EXCEPTION 'product composition activation previous generation must match current deployment state';
        END IF;

        IF NEW.generation_id = latest_generation_id THEN
            RAISE EXCEPTION 'product composition activation cannot append a no-op generation transition';
        END IF;

        IF NEW.event_kind = 'rollback'
           AND NOT EXISTS (
               SELECT 1
               FROM public.product_composition_activation_event AS prior
               WHERE prior.deployment_id = NEW.deployment_id
                 AND prior.environment_id = NEW.environment_id
                 AND prior.activation_sequence < NEW.activation_sequence
                 AND prior.generation_id = NEW.generation_id
           ) THEN
            RAISE EXCEPTION 'product composition rollback target must have been previously active';
        END IF;
    END IF;

    IF NEW.evidence_bundle_sha256 IS NOT NULL THEN
        SELECT
            evidence.valid_until_unix_ms,
            evidence.authorization_action,
            evidence.authorized_state_sequence
        INTO
            evidence_valid_until_unix_ms,
            evidence_authorization_action,
            evidence_authorized_state_sequence
        FROM public.product_composition_activation_evidence AS evidence
        WHERE evidence.evidence_bundle_sha256 = NEW.evidence_bundle_sha256
          AND evidence.deployment_id = NEW.deployment_id
          AND evidence.environment_id = NEW.environment_id
          AND evidence.generation_id = NEW.generation_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'product composition activation evidence does not bind exact deployment generation';
        END IF;

        IF evidence_authorization_action IS DISTINCT FROM NEW.event_kind
           OR evidence_authorized_state_sequence IS DISTINCT FROM NEW.activation_sequence - 1 THEN
            RAISE EXCEPTION 'product composition activation evidence does not authorize exact transition intent';
        END IF;

        wall_clock_unix_ms := floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint;
        IF wall_clock_unix_ms >= evidence_valid_until_unix_ms THEN
            RAISE EXCEPTION 'product composition activation authorization evidence is expired';
        END IF;

        IF EXISTS (
            SELECT 1
            FROM public.product_composition_route_method AS route_method
            JOIN public.product_composition_route AS route
              ON route.generation_id = route_method.generation_id
             AND route.route_id = route_method.route_id
            JOIN public.product_composition_owner_release AS owner_release
              ON owner_release.generation_id = route.generation_id
             AND owner_release.service_id = route.owner_service_id
            WHERE route_method.generation_id = NEW.generation_id
              AND (
                  route.required
                  OR EXISTS (
                      SELECT 1
                      FROM public.product_composition_activation_owner_observation AS route_observation
                      WHERE route_observation.evidence_bundle_sha256 = NEW.evidence_bundle_sha256
                        AND route_observation.generation_id = route_method.generation_id
                        AND route_observation.route_id = route_method.route_id
                  )
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM public.product_composition_activation_owner_observation AS observation
                  WHERE observation.evidence_bundle_sha256 = NEW.evidence_bundle_sha256
                    AND observation.generation_id = route_method.generation_id
                    AND observation.route_id = route_method.route_id
                    AND observation.method = route_method.method
                    AND observation.path_template = route.path_template
                    AND observation.service_id = route.owner_service_id
                    AND observation.release_version = owner_release.release_version
                    AND observation.openapi_sha256 = owner_release.openapi_sha256
                    AND observation.artifact_sha256 = owner_release.artifact_sha256
                    AND wall_clock_unix_ms < observation.valid_until_unix_ms
              )
        ) THEN
            RAISE EXCEPTION 'product composition activation evidence lacks fresh exact owner operation coverage';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.validate_product_composition_recovery_attestation_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
    latest_activation_sequence bigint;
    latest_generation_id text;
    latest_recovery_sequence bigint;
    evidence_authorization_action text;
    evidence_authorized_state_sequence bigint;
    evidence_valid_until_unix_ms bigint;
    recovery_wall_clock timestamptz;
    wall_clock_unix_ms bigint;
BEGIN
    SELECT activation_sequence, generation_id
    INTO latest_activation_sequence, latest_generation_id
    FROM public.product_composition_activation_event
    WHERE deployment_id = NEW.deployment_id
      AND environment_id = NEW.environment_id
    ORDER BY activation_sequence DESC
    LIMIT 1;

    IF latest_activation_sequence IS NULL
       OR NEW.activation_sequence IS DISTINCT FROM latest_activation_sequence
       OR NEW.generation_id IS DISTINCT FROM latest_generation_id THEN
        RAISE EXCEPTION
            'product composition recovery attestation must bind the current active generation';
    END IF;

    SELECT COALESCE(MAX(recovery_sequence), 0)
    INTO latest_recovery_sequence
    FROM public.product_composition_recovery_attestation
    WHERE deployment_id = NEW.deployment_id
      AND environment_id = NEW.environment_id;

    IF NEW.recovery_sequence <> latest_recovery_sequence + 1 THEN
        RAISE EXCEPTION
            'product composition recovery attestation sequence must advance exactly by one';
    END IF;

    SELECT
        authorization_action,
        authorized_state_sequence,
        valid_until_unix_ms
    INTO
        evidence_authorization_action,
        evidence_authorized_state_sequence,
        evidence_valid_until_unix_ms
    FROM public.product_composition_activation_evidence
    WHERE evidence_bundle_sha256 = NEW.evidence_bundle_sha256
      AND deployment_id = NEW.deployment_id
      AND environment_id = NEW.environment_id
      AND generation_id = NEW.generation_id;

    IF NOT FOUND
       OR evidence_authorization_action IS DISTINCT FROM 'recover'
       OR evidence_authorized_state_sequence IS DISTINCT FROM NEW.activation_sequence THEN
        RAISE EXCEPTION
            'product composition recovery evidence does not authorize exact active state';
    END IF;

    recovery_wall_clock := clock_timestamp();
    wall_clock_unix_ms := floor(extract(epoch FROM recovery_wall_clock) * 1000)::bigint;
    NEW.recovered_at := recovery_wall_clock;
    IF wall_clock_unix_ms >= evidence_valid_until_unix_ms THEN
        RAISE EXCEPTION 'product composition recovery authorization evidence is expired';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.product_composition_route_method AS route_method
        JOIN public.product_composition_route AS route
          ON route.generation_id = route_method.generation_id
         AND route.route_id = route_method.route_id
        JOIN public.product_composition_owner_release AS owner_release
          ON owner_release.generation_id = route.generation_id
         AND owner_release.service_id = route.owner_service_id
        WHERE route_method.generation_id = NEW.generation_id
          AND (
              route.required
              OR EXISTS (
                  SELECT 1
                  FROM public.product_composition_activation_owner_observation AS route_observation
                  WHERE route_observation.evidence_bundle_sha256 = NEW.evidence_bundle_sha256
                    AND route_observation.generation_id = route_method.generation_id
                    AND route_observation.route_id = route_method.route_id
              )
          )
          AND NOT EXISTS (
              SELECT 1
              FROM public.product_composition_activation_owner_observation AS observation
              WHERE observation.evidence_bundle_sha256 = NEW.evidence_bundle_sha256
                AND observation.generation_id = route_method.generation_id
                AND observation.route_id = route_method.route_id
                AND observation.method = route_method.method
                AND observation.path_template = route.path_template
                AND observation.service_id = route.owner_service_id
                AND observation.release_version = owner_release.release_version
                AND observation.openapi_sha256 = owner_release.openapi_sha256
                AND observation.artifact_sha256 = owner_release.artifact_sha256
                AND observation.observed_at_unix_ms <= wall_clock_unix_ms
                AND wall_clock_unix_ms < observation.valid_until_unix_ms
          )
    ) THEN
        RAISE EXCEPTION
            'product composition recovery evidence lacks fresh exact owner operation coverage';
    END IF;

    RETURN NEW;
END;
$$;

COMMIT;
