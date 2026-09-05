-- Adopt the existing validity-study registry into its canonical bounded-context schema.
-- ALTER TABLE ... SET SCHEMA preserves the relation OID, rows, constraints, indexes,
-- RLS policy and bitemporal trigger instead of copying authoritative HR evidence.

BEGIN;

CREATE ROLE workforce_validation_runtime_role NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS;

ALTER TABLE public.validity_study SET SCHEMA workforce_validation;
ALTER TABLE workforce_validation.validity_study OWNER TO workforce_validation_role;

REVOKE ALL ON TABLE workforce_validation.validity_study FROM PUBLIC;
GRANT USAGE ON SCHEMA workforce_validation TO workforce_validation_runtime_role;
GRANT SELECT ON TABLE workforce_validation.validity_study TO workforce_validation_runtime_role;
GRANT EXECUTE ON FUNCTION public.current_tenant_record_id() TO workforce_validation_runtime_role;

COMMIT;
