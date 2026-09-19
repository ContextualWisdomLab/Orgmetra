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

-- workforce_validation_role is a migration/schema-owner identity only. Runtime
-- principals must not be granted this owner role. PostgreSQL role-level GUC
-- defaults apply at login and are not re-applied by SET ROLE; because this role
-- is NOLOGIN, an ALTER ROLE ... SET search_path entry would not provide runtime
-- isolation. Future runtime adapters must use a distinct least-privilege role,
-- schema-qualified owner relations, and explicit function-level search_path for
-- any SECURITY DEFINER code.

COMMIT;
