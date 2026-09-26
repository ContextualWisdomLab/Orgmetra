BEGIN;
SET LOCAL search_path = pg_catalog, public;

-- Persist product-composition deployment activation as an append-only sequence.
-- Deployment/environment identifiers and external evidence coordinates are non-PII.
-- Remote verification happens before the deployment lock; exact evidence material is
-- persisted and rechecked against transition intent, expiry, and operation coverage
-- inside the event-insert transaction.

ALTER TABLE public.product_composition_generation
    ADD CONSTRAINT product_composition_generation_config_identity_unique
    UNIQUE (generation_id, config_sha256);

CREATE TABLE public.product_composition_deployment (
    deployment_id text NOT NULL,
    environment_id text NOT NULL,
    registered_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT product_composition_deployment_pk
        PRIMARY KEY (deployment_id, environment_id),
    CONSTRAINT product_composition_deployment_id_check
        CHECK (
            char_length(deployment_id) BETWEEN 1 AND 64
            AND deployment_id ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
        ),
    CONSTRAINT product_composition_environment_id_check
        CHECK (
            char_length(environment_id) BETWEEN 1 AND 64
            AND environment_id ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
        )
);

CREATE TABLE public.product_composition_activation_evidence (
    evidence_bundle_sha256 text NOT NULL,
    deployment_id text NOT NULL,
    environment_id text NOT NULL,
    generation_id text NOT NULL,
    config_sha256 text NOT NULL,
    authorization_action text NOT NULL,
    authorized_state_sequence bigint NOT NULL,
    keyverse_release_version text NOT NULL,
    keyverse_artifact_sha256 text NOT NULL,
    keyverse_release_locator text NOT NULL,
    orgmetra_release_version text NOT NULL,
    orgmetra_artifact_sha256 text NOT NULL,
    orgmetra_release_locator text NOT NULL,
    orgmetra_policy_version_code text NOT NULL,
    authorization_decision_sha256 text NOT NULL,
    valid_until_unix_ms bigint NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT product_composition_activation_evidence_pk
        PRIMARY KEY (evidence_bundle_sha256),
    CONSTRAINT product_composition_activation_evidence_bundle_generation_unique
        UNIQUE (evidence_bundle_sha256, generation_id),
    CONSTRAINT product_composition_activation_evidence_binding_unique
        UNIQUE (
            evidence_bundle_sha256,
            deployment_id,
            environment_id,
            generation_id
        ),
    CONSTRAINT product_composition_activation_evidence_deployment_fk
        FOREIGN KEY (deployment_id, environment_id)
        REFERENCES public.product_composition_deployment(deployment_id, environment_id),
    CONSTRAINT product_composition_activation_evidence_generation_fk
        FOREIGN KEY (generation_id, config_sha256)
        REFERENCES public.product_composition_generation(generation_id, config_sha256),
    CONSTRAINT product_composition_activation_evidence_bundle_digest_check
        CHECK (evidence_bundle_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT product_composition_activation_evidence_action_check
        CHECK (authorization_action IN ('activate', 'rollback', 'recover')),
    CONSTRAINT product_composition_activation_evidence_state_sequence_check
        CHECK (authorized_state_sequence >= 0),
    CONSTRAINT product_composition_activation_evidence_keyverse_artifact_check
        CHECK (keyverse_artifact_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT product_composition_activation_evidence_orgmetra_artifact_check
        CHECK (orgmetra_artifact_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT product_composition_activation_evidence_authorization_digest_check
        CHECK (authorization_decision_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT product_composition_activation_evidence_config_digest_check
        CHECK (config_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT product_composition_activation_evidence_keyverse_release_check
        CHECK (
            char_length(keyverse_release_version) BETWEEN 1 AND 64
            AND keyverse_release_version ~ '^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$'
            AND lower(keyverse_release_version) NOT IN ('develop', 'head', 'latest', 'main', 'master')
            AND lower(keyverse_release_version) NOT LIKE 'refs/%'
            AND lower(keyverse_release_version) NOT LIKE 'pr-%'
            AND keyverse_release_locator =
                'https://github.com/ContextualWisdomLab/keyverse/releases/tag/'
                || keyverse_release_version
        ),
    CONSTRAINT product_composition_activation_evidence_orgmetra_release_check
        CHECK (
            char_length(orgmetra_release_version) BETWEEN 1 AND 64
            AND orgmetra_release_version ~ '^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$'
            AND lower(orgmetra_release_version) NOT IN ('develop', 'head', 'latest', 'main', 'master')
            AND lower(orgmetra_release_version) NOT LIKE 'refs/%'
            AND lower(orgmetra_release_version) NOT LIKE 'pr-%'
            AND orgmetra_release_locator =
                'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/'
                || orgmetra_release_version
        ),
    CONSTRAINT product_composition_activation_evidence_policy_version_check
        CHECK (
            char_length(orgmetra_policy_version_code) BETWEEN 1 AND 128
            AND orgmetra_policy_version_code ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'
        ),
    CONSTRAINT product_composition_activation_evidence_expiry_check
        CHECK (valid_until_unix_ms > 0)
);

CREATE TABLE public.product_composition_activation_owner_observation (
    evidence_bundle_sha256 text NOT NULL,
    generation_id text NOT NULL,
    route_id text NOT NULL,
    method text NOT NULL,
    path_template text NOT NULL,
    service_id text NOT NULL,
    release_version text NOT NULL,
    openapi_sha256 text NOT NULL,
    artifact_sha256 text NOT NULL,
    observation_sha256 text NOT NULL,
    observed_at_unix_ms bigint NOT NULL,
    valid_until_unix_ms bigint NOT NULL,
    CONSTRAINT product_composition_activation_owner_observation_pk
        PRIMARY KEY (evidence_bundle_sha256, route_id, method),
    CONSTRAINT product_composition_activation_owner_observation_evidence_fk
        FOREIGN KEY (evidence_bundle_sha256, generation_id)
        REFERENCES public.product_composition_activation_evidence(
            evidence_bundle_sha256,
            generation_id
        ),
    CONSTRAINT product_composition_activation_owner_observation_route_method_fk
        FOREIGN KEY (generation_id, route_id, method)
        REFERENCES public.product_composition_route_method(generation_id, route_id, method),
    CONSTRAINT product_composition_activation_owner_observation_owner_fk
        FOREIGN KEY (generation_id, service_id)
        REFERENCES public.product_composition_owner_release(generation_id, service_id),
    CONSTRAINT product_composition_activation_owner_observation_release_check
        CHECK (
            char_length(release_version) BETWEEN 1 AND 64
            AND release_version ~ '^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$'
            AND lower(release_version) NOT IN ('develop', 'head', 'latest', 'main', 'master')
            AND lower(release_version) NOT LIKE 'refs/%'
            AND lower(release_version) NOT LIKE 'pr-%'
        ),
    CONSTRAINT product_composition_activation_owner_observation_openapi_check
        CHECK (openapi_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT product_composition_activation_owner_observation_artifact_check
        CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT product_composition_activation_owner_observation_digest_check
        CHECK (observation_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT product_composition_activation_owner_observation_time_check
        CHECK (
            observed_at_unix_ms > 0
            AND valid_until_unix_ms > observed_at_unix_ms
        )
);

CREATE TABLE public.product_composition_activation_event (
    deployment_id text NOT NULL,
    environment_id text NOT NULL,
    activation_sequence bigint NOT NULL,
    generation_id text NOT NULL,
    previous_generation_id text NULL,
    event_kind text NOT NULL,
    evidence_bundle_sha256 text NULL,
    activated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT product_composition_activation_event_pk
        PRIMARY KEY (deployment_id, environment_id, activation_sequence),
    CONSTRAINT product_composition_activation_event_deployment_fk
        FOREIGN KEY (deployment_id, environment_id)
        REFERENCES public.product_composition_deployment(deployment_id, environment_id),
    CONSTRAINT product_composition_activation_event_generation_fk
        FOREIGN KEY (generation_id)
        REFERENCES public.product_composition_generation(generation_id),
    CONSTRAINT product_composition_activation_event_previous_generation_fk
        FOREIGN KEY (previous_generation_id)
        REFERENCES public.product_composition_generation(generation_id),
    CONSTRAINT product_composition_activation_event_evidence_fk
        FOREIGN KEY (
            evidence_bundle_sha256,
            deployment_id,
            environment_id,
            generation_id
        )
        REFERENCES public.product_composition_activation_evidence(
            evidence_bundle_sha256,
            deployment_id,
            environment_id,
            generation_id
        ),
    CONSTRAINT product_composition_activation_event_sequence_check
        CHECK (activation_sequence > 0),
    CONSTRAINT product_composition_activation_event_kind_check
        CHECK (event_kind IN ('activate', 'rollback')),
    CONSTRAINT product_composition_activation_event_evidence_digest_check
        CHECK (
            evidence_bundle_sha256 IS NULL
            OR evidence_bundle_sha256 ~ '^[0-9a-f]{64}$'
        ),
    CONSTRAINT product_composition_activation_event_first_previous_check
        CHECK (
            (activation_sequence = 1 AND previous_generation_id IS NULL)
            OR (activation_sequence > 1 AND previous_generation_id IS NOT NULL)
        )
);

CREATE INDEX product_composition_activation_event_generation_idx
    ON public.product_composition_activation_event (
        deployment_id,
        environment_id,
        generation_id,
        activation_sequence
    );

CREATE FUNCTION public.validate_product_composition_activation_observation_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
    expected_path_template text;
    expected_service_id text;
    expected_release_version text;
    expected_openapi_sha256 text;
    expected_artifact_sha256 text;
    evidence_valid_until_unix_ms bigint;
BEGIN
    SELECT
        route.path_template,
        route.owner_service_id,
        owner_release.release_version,
        owner_release.openapi_sha256,
        owner_release.artifact_sha256
    INTO
        expected_path_template,
        expected_service_id,
        expected_release_version,
        expected_openapi_sha256,
        expected_artifact_sha256
    FROM public.product_composition_route AS route
    JOIN public.product_composition_owner_release AS owner_release
      ON owner_release.generation_id = route.generation_id
     AND owner_release.service_id = route.owner_service_id
    WHERE route.generation_id = NEW.generation_id
      AND route.route_id = NEW.route_id;

    IF NOT FOUND
       OR NEW.path_template IS DISTINCT FROM expected_path_template
       OR NEW.service_id IS DISTINCT FROM expected_service_id
       OR NEW.release_version IS DISTINCT FROM expected_release_version
       OR NEW.openapi_sha256 IS DISTINCT FROM expected_openapi_sha256
       OR NEW.artifact_sha256 IS DISTINCT FROM expected_artifact_sha256 THEN
        RAISE EXCEPTION 'product composition owner observation does not match exact generation authority';
    END IF;

    SELECT valid_until_unix_ms
    INTO evidence_valid_until_unix_ms
    FROM public.product_composition_activation_evidence
    WHERE evidence_bundle_sha256 = NEW.evidence_bundle_sha256
      AND generation_id = NEW.generation_id;

    IF NOT FOUND OR NEW.valid_until_unix_ms < evidence_valid_until_unix_ms THEN
        RAISE EXCEPTION 'product composition owner observation does not cover activation evidence lifetime';
    END IF;

    RETURN NEW;
END;
$$;

CREATE FUNCTION public.validate_product_composition_activation_insert()
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

CREATE FUNCTION public.reject_product_composition_activation_registry_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    RAISE EXCEPTION 'product composition activation registry is append-only; TRUNCATE is not allowed';
END;
$$;

CREATE TRIGGER product_composition_activation_owner_observation_insert_guard
BEFORE INSERT ON public.product_composition_activation_owner_observation
FOR EACH ROW
EXECUTE FUNCTION public.validate_product_composition_activation_observation_insert();

CREATE TRIGGER product_composition_activation_event_lineage_guard
BEFORE INSERT ON public.product_composition_activation_event
FOR EACH ROW
EXECUTE FUNCTION public.validate_product_composition_activation_insert();

CREATE TRIGGER product_composition_deployment_append_only_guard
BEFORE UPDATE OR DELETE ON public.product_composition_deployment
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

CREATE TRIGGER product_composition_activation_evidence_append_only_guard
BEFORE UPDATE OR DELETE ON public.product_composition_activation_evidence
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

CREATE TRIGGER product_composition_activation_owner_observation_append_only_guard
BEFORE UPDATE OR DELETE ON public.product_composition_activation_owner_observation
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

CREATE TRIGGER product_composition_activation_event_append_only_guard
BEFORE UPDATE OR DELETE ON public.product_composition_activation_event
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

CREATE TRIGGER product_composition_deployment_truncate_guard
BEFORE TRUNCATE ON public.product_composition_deployment
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_product_composition_activation_registry_truncate();

CREATE TRIGGER product_composition_activation_evidence_truncate_guard
BEFORE TRUNCATE ON public.product_composition_activation_evidence
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_product_composition_activation_registry_truncate();

CREATE TRIGGER product_composition_activation_owner_observation_truncate_guard
BEFORE TRUNCATE ON public.product_composition_activation_owner_observation
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_product_composition_activation_registry_truncate();

CREATE TRIGGER product_composition_activation_event_truncate_guard
BEFORE TRUNCATE ON public.product_composition_activation_event
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_product_composition_activation_registry_truncate();

COMMIT;
