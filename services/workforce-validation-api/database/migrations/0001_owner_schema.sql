-- Establish the logical PostgreSQL ownership boundary for workforce_validation.
-- This migration intentionally creates no application table. Legacy foundation
-- validity-study tables stay untouched until an explicit forward-only adoption
-- migration can preserve existing foreign-key and acceptance contracts.

BEGIN;

CREATE ROLE workforce_validation_role NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS;

CREATE SCHEMA workforce_validation AUTHORIZATION workforce_validation_role;
REVOKE ALL ON SCHEMA workforce_validation FROM PUBLIC;

-- Any login role granted this owner role resolves only owner objects and the
-- PostgreSQL catalog by default. Cross-context application tables are never put
-- on the implicit search path.
ALTER ROLE workforce_validation_role SET search_path = workforce_validation, pg_catalog;

COMMIT;
