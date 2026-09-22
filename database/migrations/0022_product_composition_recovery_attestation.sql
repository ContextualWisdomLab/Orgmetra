-- Persist each successful recovery re-admission as append-only durable evidence.
-- Remote verification still happens before the deployment lock. The local transaction
-- rechecks the exact active activation sequence/generation, persists the evidence bundle,
-- and appends one recovery attestation while holding that deployment lock.
-- Create the table, validation function, and all mutation guards atomically so concurrent
-- sessions can never observe an unguarded recovery-attestation relation during upgrade.

BEGIN;

CREATE TABLE public.product_composition_recovery_attestation (
    deployment_id text NOT NULL,
    environment_id text NOT NULL,
    recovery_sequence bigint NOT NULL,
    activation_sequence bigint NOT NULL,
    generation_id text NOT NULL,
    evidence_bundle_sha256 text NOT NULL,
    recovered_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT product_composition_recovery_attestation_pk
        PRIMARY KEY (deployment_id, environment_id, recovery_sequence),
    CONSTRAINT product_composition_recovery_attestation_deployment_fk
        FOREIGN KEY (deployment_id, environment_id)
        REFERENCES public.product_composition_deployment(deployment_id, environment_id),
    CONSTRAINT product_composition_recovery_attestation_activation_fk
        FOREIGN KEY (deployment_id, environment_id, activation_sequence)
        REFERENCES public.product_composition_activation_event(
            deployment_id,
            environment_id,
            activation_sequence
        ),
    CONSTRAINT product_composition_recovery_attestation_generation_fk
        FOREIGN KEY (generation_id)
        REFERENCES public.product_composition_generation(generation_id),
    CONSTRAINT product_composition_recovery_attestation_evidence_fk
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
    CONSTRAINT product_composition_recovery_attestation_sequence_check
        CHECK (recovery_sequence > 0),
    CONSTRAINT product_composition_recovery_attestation_activation_sequence_check
        CHECK (activation_sequence > 0),
    CONSTRAINT product_composition_recovery_attestation_evidence_digest_check
        CHECK (evidence_bundle_sha256 ~ '^[0-9a-f]{64}$')
);

CREATE FUNCTION validate_product_composition_recovery_attestation_insert()
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

    wall_clock_unix_ms := floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint;
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

CREATE TRIGGER product_composition_recovery_attestation_insert_guard
BEFORE INSERT ON public.product_composition_recovery_attestation
FOR EACH ROW
EXECUTE FUNCTION validate_product_composition_recovery_attestation_insert();

CREATE TRIGGER product_composition_recovery_attestation_append_only_guard
BEFORE UPDATE OR DELETE ON public.product_composition_recovery_attestation
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER product_composition_recovery_attestation_truncate_guard
BEFORE TRUNCATE ON public.product_composition_recovery_attestation
FOR EACH STATEMENT
EXECUTE FUNCTION reject_product_composition_activation_registry_truncate();

COMMIT;
