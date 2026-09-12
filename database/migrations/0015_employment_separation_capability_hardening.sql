-- Keep the high-impact Employment separation transition behind an explicitly
-- granted database capability. PostgreSQL grants EXECUTE on new functions to
-- PUBLIC by default; leaving that default in place would let any sufficiently
-- privileged application role bypass the reviewed People/Keyverse boundary.
--
-- The function remains SECURITY INVOKER. A later service-role grant must be
-- explicit and must not turn this function into a privilege-escalation owner.

BEGIN;

SET LOCAL search_path = pg_catalog, public;

REVOKE EXECUTE ON FUNCTION public.separate_employment_record_once(
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

REVOKE EXECUTE ON FUNCTION public.reject_employment_separation_truncate() FROM PUBLIC;

COMMIT;
