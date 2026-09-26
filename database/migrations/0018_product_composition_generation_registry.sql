BEGIN;
SET LOCAL search_path = pg_catalog, public;

-- Persist admitted product-composition generations as immutable normalized authority.
-- These tables own routing configuration only. They intentionally contain no HR domain,
-- tenant, Keyverse, Person, Employment, Job, Position, Assignment, or assessment truth.
-- A generation identifier is never reassigned: callers may repeat the exact same material,
-- while any semantic successor must receive a new generation_id.
--
-- Migration-session search_path is not authority. All owned objects and trigger bindings are
-- pinned to public while built-ins resolve through pg_catalog first, so a caller-controlled
-- schema cannot redirect registry creation, foreign keys, or mutation guards.

CREATE TABLE public.product_composition_generation (
    generation_id text PRIMARY KEY,
    schema_version text NOT NULL,
    config_sha256 text NOT NULL,
    registered_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT product_composition_generation_id_check
        CHECK (
            char_length(generation_id) BETWEEN 1 AND 64
            AND generation_id ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
        ),
    CONSTRAINT product_composition_generation_schema_check
        CHECK (schema_version = 'orgmetra_gateway_composition.v1'),
    CONSTRAINT product_composition_generation_digest_check
        CHECK (config_sha256 ~ '^[0-9a-f]{64}$')
);

CREATE TABLE public.product_composition_owner_release (
    generation_id text NOT NULL,
    service_id text NOT NULL,
    release_version text NOT NULL,
    openapi_sha256 text NOT NULL,
    artifact_sha256 text NOT NULL,
    release_locator text NOT NULL,
    CONSTRAINT product_composition_owner_release_pk
        PRIMARY KEY (generation_id, service_id),
    CONSTRAINT product_composition_owner_release_generation_fk
        FOREIGN KEY (generation_id)
        REFERENCES public.product_composition_generation(generation_id),
    CONSTRAINT product_composition_owner_release_service_check
        CHECK (
            char_length(service_id) BETWEEN 1 AND 64
            AND service_id ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
        ),
    CONSTRAINT product_composition_owner_release_version_check
        CHECK (
            char_length(release_version) BETWEEN 1 AND 64
            AND release_version ~ '^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$'
            AND lower(release_version) NOT IN ('develop', 'head', 'latest', 'main', 'master')
            AND lower(release_version) NOT LIKE 'refs/%'
            AND lower(release_version) NOT LIKE 'pr-%'
        ),
    CONSTRAINT product_composition_owner_release_openapi_digest_check
        CHECK (openapi_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT product_composition_owner_release_artifact_digest_check
        CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT product_composition_owner_release_locator_check
        CHECK (
            release_locator =
                'https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/' || release_version
        )
);

CREATE TABLE public.product_composition_route (
    generation_id text NOT NULL,
    route_id text NOT NULL,
    path_template text NOT NULL,
    owner_service_id text NOT NULL,
    logical_upstream text NOT NULL,
    required boolean NOT NULL,
    CONSTRAINT product_composition_route_pk
        PRIMARY KEY (generation_id, route_id),
    CONSTRAINT product_composition_route_generation_fk
        FOREIGN KEY (generation_id)
        REFERENCES public.product_composition_generation(generation_id),
    CONSTRAINT product_composition_route_owner_release_fk
        FOREIGN KEY (generation_id, owner_service_id)
        REFERENCES public.product_composition_owner_release(generation_id, service_id),
    CONSTRAINT product_composition_route_id_check
        CHECK (
            char_length(route_id) BETWEEN 1 AND 64
            AND route_id ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
        ),
    CONSTRAINT product_composition_route_path_length_check
        CHECK (char_length(path_template) BETWEEN 1 AND 256),
    CONSTRAINT product_composition_route_upstream_check
        CHECK (
            logical_upstream = 'service://' || replace(owner_service_id, '_', '-')
        )
);

CREATE TABLE public.product_composition_route_method (
    generation_id text NOT NULL,
    route_id text NOT NULL,
    method text NOT NULL,
    CONSTRAINT product_composition_route_method_pk
        PRIMARY KEY (generation_id, route_id, method),
    CONSTRAINT product_composition_route_method_route_fk
        FOREIGN KEY (generation_id, route_id)
        REFERENCES public.product_composition_route(generation_id, route_id),
    CONSTRAINT product_composition_route_method_value_check
        CHECK (method IN ('DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT'))
);

CREATE FUNCTION public.reject_product_composition_generation_registry_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    RAISE EXCEPTION 'product composition generation registry is append-only; TRUNCATE is not allowed';
END;
$$;

CREATE TRIGGER product_composition_generation_append_only_guard
BEFORE UPDATE OR DELETE ON public.product_composition_generation
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

CREATE TRIGGER product_composition_owner_release_append_only_guard
BEFORE UPDATE OR DELETE ON public.product_composition_owner_release
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

CREATE TRIGGER product_composition_route_append_only_guard
BEFORE UPDATE OR DELETE ON public.product_composition_route
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

CREATE TRIGGER product_composition_route_method_append_only_guard
BEFORE UPDATE OR DELETE ON public.product_composition_route_method
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

CREATE TRIGGER product_composition_generation_truncate_guard
BEFORE TRUNCATE ON public.product_composition_generation
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_product_composition_generation_registry_truncate();

CREATE TRIGGER product_composition_owner_release_truncate_guard
BEFORE TRUNCATE ON public.product_composition_owner_release
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_product_composition_generation_registry_truncate();

CREATE TRIGGER product_composition_route_truncate_guard
BEFORE TRUNCATE ON public.product_composition_route
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_product_composition_generation_registry_truncate();

CREATE TRIGGER product_composition_route_method_truncate_guard
BEFORE TRUNCATE ON public.product_composition_route_method
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_product_composition_generation_registry_truncate();

COMMIT;
