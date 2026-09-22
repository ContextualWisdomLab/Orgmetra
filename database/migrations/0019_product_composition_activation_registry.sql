-- Persist product-composition deployment activation as an append-only sequence.
-- Deployment/environment identifiers are non-PII composition coordinates. Activation
-- references only immutable generations from migration 0018; rollback is represented
-- as another event and never rewrites prior state.

CREATE TABLE product_composition_deployment (
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

CREATE TABLE product_composition_activation_event (
    deployment_id text NOT NULL,
    environment_id text NOT NULL,
    activation_sequence bigint NOT NULL,
    generation_id text NOT NULL,
    previous_generation_id text NULL,
    event_kind text NOT NULL,
    activated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT product_composition_activation_event_pk
        PRIMARY KEY (deployment_id, environment_id, activation_sequence),
    CONSTRAINT product_composition_activation_event_deployment_fk
        FOREIGN KEY (deployment_id, environment_id)
        REFERENCES product_composition_deployment(deployment_id, environment_id),
    CONSTRAINT product_composition_activation_event_generation_fk
        FOREIGN KEY (generation_id)
        REFERENCES product_composition_generation(generation_id),
    CONSTRAINT product_composition_activation_event_previous_generation_fk
        FOREIGN KEY (previous_generation_id)
        REFERENCES product_composition_generation(generation_id),
    CONSTRAINT product_composition_activation_event_sequence_check
        CHECK (activation_sequence > 0),
    CONSTRAINT product_composition_activation_event_kind_check
        CHECK (event_kind IN ('activate', 'rollback')),
    CONSTRAINT product_composition_activation_event_first_previous_check
        CHECK (
            (activation_sequence = 1 AND previous_generation_id IS NULL)
            OR (activation_sequence > 1 AND previous_generation_id IS NOT NULL)
        )
);

CREATE INDEX product_composition_activation_event_generation_idx
    ON product_composition_activation_event (
        deployment_id,
        environment_id,
        generation_id,
        activation_sequence
    );

CREATE FUNCTION validate_product_composition_activation_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
    latest_sequence bigint;
    latest_generation_id text;
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
        RETURN NEW;
    END IF;

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

    RETURN NEW;
END;
$$;

CREATE FUNCTION reject_product_composition_activation_registry_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    RAISE EXCEPTION 'product composition activation registry is append-only; TRUNCATE is not allowed';
END;
$$;

CREATE TRIGGER product_composition_activation_event_lineage_guard
BEFORE INSERT ON product_composition_activation_event
FOR EACH ROW
EXECUTE FUNCTION validate_product_composition_activation_insert();

CREATE TRIGGER product_composition_deployment_append_only_guard
BEFORE UPDATE OR DELETE ON product_composition_deployment
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER product_composition_activation_event_append_only_guard
BEFORE UPDATE OR DELETE ON product_composition_activation_event
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER product_composition_deployment_truncate_guard
BEFORE TRUNCATE ON product_composition_deployment
FOR EACH STATEMENT
EXECUTE FUNCTION reject_product_composition_activation_registry_truncate();

CREATE TRIGGER product_composition_activation_event_truncate_guard
BEFORE TRUNCATE ON product_composition_activation_event
FOR EACH STATEMENT
EXECUTE FUNCTION reject_product_composition_activation_registry_truncate();
