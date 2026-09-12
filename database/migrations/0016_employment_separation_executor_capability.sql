-- Make the governed Employment separation transition callable without granting
-- the application direct mutation rights on People or audit/outbox relations.
-- The externally assignable executor receives only function EXECUTE; a dedicated
-- NOLOGIN/NOBYPASSRLS owner holds the minimum database privileges used by the
-- reviewed SECURITY DEFINER boundary.

-- Capability role names are security boundaries. Reusing an existing cluster
-- role could preserve undisclosed memberships or ACLs. Fail before changing any
-- project object so a collision cannot leave a partially elevated boundary.
DO $orgmetra_employment_separation_role_preflight$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_catalog.pg_roles
        WHERE rolname IN (
            'orgmetra_employment_separation_owner',
            'orgmetra_employment_separation_executor'
        )
    ) THEN
        RAISE EXCEPTION 'pre-existing Employment separation capability role is not accepted'
            USING ERRCODE = '42710';
    END IF;
END;
$orgmetra_employment_separation_role_preflight$;

BEGIN;

SET LOCAL search_path = pg_catalog, public;

CREATE ROLE orgmetra_employment_separation_owner
    NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS;

CREATE ROLE orgmetra_employment_separation_executor
    NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS;

GRANT USAGE ON SCHEMA public
    TO orgmetra_employment_separation_owner,
       orgmetra_employment_separation_executor;

-- The function owner is not a login/runtime principal. These grants are only the
-- capabilities needed by separate_employment_record_once and its audited write
-- helper while FORCE RLS remains active under the caller's tenant context.
GRANT SELECT ON TABLE
    public.employment_record,
    public.employment_record_version,
    public.assignment_record,
    public.employment_separation_record,
    public.people_mutation_idempotency_record
TO orgmetra_employment_separation_owner;

-- SELECT ... FOR UPDATE on the aggregate roots requires update capability. The
-- only business mutation performed by the boundary is recorded_to on the exact
-- current Employment version; the owner remains NOLOGIN and is not grantable as
-- the application capability.
GRANT UPDATE (recorded_from) ON TABLE public.employment_record
    TO orgmetra_employment_separation_owner;
GRANT UPDATE (recorded_to) ON TABLE public.employment_record_version
    TO orgmetra_employment_separation_owner;

GRANT INSERT ON TABLE
    public.employment_record_version,
    public.employment_separation_record,
    public.people_mutation_idempotency_record,
    public.audit_event_record,
    public.outbox_delivery_record
TO orgmetra_employment_separation_owner;

GRANT EXECUTE ON FUNCTION public.current_tenant_record_id()
    TO orgmetra_employment_separation_owner;
GRANT EXECUTE ON FUNCTION public.is_operational_uuid(uuid)
    TO orgmetra_employment_separation_owner;
GRANT EXECUTE ON FUNCTION public.digest(bytea, text)
    TO orgmetra_employment_separation_owner;
GRANT EXECUTE ON FUNCTION public.validate_audit_event_envelope(text, uuid, uuid, text)
    TO orgmetra_employment_separation_owner;
GRANT EXECUTE ON FUNCTION public.record_audit_outbox_event(uuid, uuid, uuid, text, text, text)
    TO orgmetra_employment_separation_owner;

-- ALTER FUNCTION OWNER requires CREATE on the containing schema for the target
-- owner. Grant that authority only for this atomic handoff and revoke it before
-- commit. PUBLIC remains unable to execute the high-impact mutation boundary.
GRANT CREATE ON SCHEMA public TO orgmetra_employment_separation_owner;
ALTER FUNCTION public.separate_employment_record_once(
    uuid,
    uuid,
    uuid,
    uuid,
    date,
    text,
    text,
    text,
    text,
    text,
    text,
    text,
    uuid,
    uuid
) OWNER TO orgmetra_employment_separation_owner;
ALTER FUNCTION public.separate_employment_record_once(
    uuid,
    uuid,
    uuid,
    uuid,
    date,
    text,
    text,
    text,
    text,
    text,
    text,
    text,
    uuid,
    uuid
) SECURITY DEFINER;
REVOKE CREATE ON SCHEMA public FROM orgmetra_employment_separation_owner;
REVOKE ALL ON FUNCTION public.separate_employment_record_once(
    uuid,
    uuid,
    uuid,
    uuid,
    date,
    text,
    text,
    text,
    text,
    text,
    text,
    text,
    uuid,
    uuid
) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.separate_employment_record_once(
    uuid,
    uuid,
    uuid,
    uuid,
    date,
    text,
    text,
    text,
    text,
    text,
    text,
    text,
    uuid,
    uuid
) TO orgmetra_employment_separation_executor;

COMMENT ON FUNCTION public.separate_employment_record_once(
    uuid,
    uuid,
    uuid,
    uuid,
    date,
    text,
    text,
    text,
    text,
    text,
    text,
    text,
    uuid,
    uuid
) IS
    'Performs one tenant-bound, idempotent, bitemporal Employment separation. The SECURITY DEFINER function is owned by a dedicated NOLOGIN/NOBYPASSRLS role with only the reviewed People and audit/outbox privileges required by this transaction. The externally assignable executor has schema USAGE plus function EXECUTE only and cannot bypass the governed transition with direct table DML. FORCE RLS and the explicit current_tenant_record_id check remain active.';

COMMIT;
