-- Prevent an older transaction from reconstructing hierarchy truth at its
-- earlier transaction timestamp after a later-started hierarchy change commits.
-- The authoritative mutation uses a tenant-scoped advisory lock, but PostgreSQL
-- transaction_timestamp() is fixed at transaction start. A transaction that
-- started earlier can therefore acquire the lock later and otherwise evaluate
-- pre-change bitemporal truth. Reject that transaction and require a retry.

CREATE FUNCTION reject_stale_organization_hierarchy_transaction()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM organization_unit AS unit
        WHERE unit.tenant_record_id = NEW.tenant_record_id
          AND (
              unit.recorded_from > NEW.recorded_at
              OR unit.recorded_to > NEW.recorded_at
          )
    ) OR EXISTS (
        SELECT 1
        FROM organization_unit_version AS version
        WHERE version.tenant_record_id = NEW.tenant_record_id
          AND (
              version.recorded_from > NEW.recorded_at
              OR version.recorded_to > NEW.recorded_at
          )
    ) THEN
        RAISE EXCEPTION 'restart organization hierarchy application after concurrent hierarchy change'
            USING ERRCODE = '40001';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION reject_stale_organization_hierarchy_transaction() IS
    'Fails closed when tenant Organization truth changed after the applying transaction began, preventing pre-lock transaction time from reconstructing stale hierarchy truth after a later commit.';

CREATE TRIGGER organization_hierarchy_application_concurrency_guard
BEFORE INSERT ON organization_hierarchy_change_application_record
FOR EACH ROW
EXECUTE FUNCTION reject_stale_organization_hierarchy_transaction();
