-- Serialize Assignment creation against Employment separation on the Employment aggregate.
--
-- Separation already locks employment_record before it inspects Assignment truth. Assignment
-- creation must acquire the same anchor lock before INSERT and then re-read current Employment
-- versions under READ COMMITTED. This closes the check/insert race in both directions without
-- holding an external workflow or broad table lock inside the transaction.
--
-- PostgreSQL requires UPDATE privilege for SELECT ... FOR UPDATE. Do not widen the ordinary
-- Assignment writer merely to obtain the conflict lock: a dedicated NOLOGIN/NOBYPASSRLS owner
-- executes the trigger with only the reviewed read/anchor-lock capabilities, while FORCE RLS
-- continues to bind every lookup to the caller's transaction-local tenant context.

DO $orgmetra_assignment_employment_guard_role_preflight$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_catalog.pg_roles
        WHERE rolname = 'orgmetra_assignment_employment_guard_owner'
    ) THEN
        RAISE EXCEPTION 'pre-existing Assignment Employment guard capability role is not accepted'
            USING ERRCODE = '42710';
    END IF;
END;
$orgmetra_assignment_employment_guard_role_preflight$;

BEGIN;

SET LOCAL search_path = pg_catalog, public;

CREATE ROLE orgmetra_assignment_employment_guard_owner
    NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS;

GRANT USAGE ON SCHEMA public TO orgmetra_assignment_employment_guard_owner;
GRANT SELECT ON TABLE
    public.employment_record,
    public.employment_record_version
TO orgmetra_assignment_employment_guard_owner;

-- SELECT ... FOR UPDATE requires an UPDATE privilege. Grant only one inert anchor
-- column; the trigger never mutates employment_record and the role is not a login.
GRANT UPDATE (recorded_from) ON TABLE public.employment_record
    TO orgmetra_assignment_employment_guard_owner;
GRANT EXECUTE ON FUNCTION public.current_tenant_record_id()
    TO orgmetra_assignment_employment_guard_owner;

CREATE FUNCTION public.guard_assignment_employment_coverage()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    v_anchor_person_id uuid;
    v_has_covering_employment boolean;
BEGIN
    SELECT employment.person_record_id
    INTO v_anchor_person_id
    FROM public.employment_record AS employment
    WHERE employment.tenant_record_id = NEW.tenant_record_id
      AND employment.employment_record_id = NEW.employment_record_id
    FOR UPDATE OF employment;

    IF NOT FOUND OR v_anchor_person_id IS DISTINCT FROM NEW.person_record_id THEN
        RAISE EXCEPTION 'assignment target does not match tenant person and employment'
            USING ERRCODE = '23503';
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM public.employment_record_version AS version
        WHERE version.tenant_record_id = NEW.tenant_record_id
          AND version.employment_record_id = NEW.employment_record_id
          AND version.recorded_to IS NULL
          AND version.employment_status_code IN ('active', 'leave')
          AND version.effective_from <= NEW.effective_from
          AND (
                version.effective_to IS NULL
                OR (
                    NEW.effective_to IS NOT NULL
                    AND NEW.effective_to <= version.effective_to
                )
          )
    )
    INTO v_has_covering_employment;

    IF v_has_covering_employment IS NOT TRUE THEN
        RAISE EXCEPTION 'assignment requires current active or leave Employment coverage'
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$$;

GRANT CREATE ON SCHEMA public TO orgmetra_assignment_employment_guard_owner;
ALTER FUNCTION public.guard_assignment_employment_coverage()
    OWNER TO orgmetra_assignment_employment_guard_owner;
ALTER FUNCTION public.guard_assignment_employment_coverage()
    SECURITY DEFINER;
REVOKE CREATE ON SCHEMA public FROM orgmetra_assignment_employment_guard_owner;
REVOKE ALL ON FUNCTION public.guard_assignment_employment_coverage() FROM PUBLIC;

CREATE TRIGGER assignment_employment_coverage_guard
BEFORE INSERT ON public.assignment_record
FOR EACH ROW
EXECUTE FUNCTION public.guard_assignment_employment_coverage();

COMMENT ON FUNCTION public.guard_assignment_employment_coverage() IS
    'Serializes Assignment INSERT against Employment separation using the shared Employment anchor, then proves the inserted Assignment interval remains fully covered by a current active/leave Employment version. The SECURITY DEFINER owner is a dedicated NOLOGIN/NOBYPASSRLS role with only tenant-scoped read and anchor-lock capability.';

COMMIT;
