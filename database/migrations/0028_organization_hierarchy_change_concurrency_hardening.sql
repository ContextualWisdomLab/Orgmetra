-- Prevent an older transaction from reconstructing hierarchy truth at its
-- earlier transaction timestamp after a later-started hierarchy change commits.
-- The authoritative mutation uses a tenant-scoped advisory lock, but PostgreSQL
-- transaction_timestamp() is fixed at transaction start. A transaction that
-- started earlier can therefore acquire the lock later and otherwise evaluate
-- pre-change bitemporal truth. Reject that transaction and require a retry.

-- The stale guard is on the mutation path, so its tenant/time probes must not
-- degrade into tenant-history scans as bitemporal Organization truth grows.
-- This migration MUST run through psql (or a runner with equivalent \gexec
-- semantics) in autocommit mode: PostgreSQL forbids CREATE/DROP INDEX
-- CONCURRENTLY inside an explicit transaction block.
--
-- A cancelled concurrent build can leave an INVALID same-named index. Remove
-- only that residue before creating each governed index. Valid indexes from an
-- earlier partial attempt are preserved and skipped by IF NOT EXISTS, allowing
-- the entire migration to be retried without discarding successful work.
SELECT format(
    'DROP INDEX CONCURRENTLY IF EXISTS %I.%I;',
    namespace.nspname,
    index_class.relname
)
FROM pg_class AS index_class
JOIN pg_namespace AS namespace
  ON namespace.oid = index_class.relnamespace
JOIN pg_index AS index_state
  ON index_state.indexrelid = index_class.oid
WHERE namespace.nspname = 'public'
  AND index_class.relname IN (
      'organization_unit_tenant_recorded_from_idx',
      'organization_unit_tenant_recorded_to_idx',
      'organization_unit_version_tenant_recorded_from_idx',
      'organization_unit_version_tenant_recorded_to_idx'
  )
  AND NOT index_state.indisvalid
ORDER BY index_class.relname
\gexec

CREATE INDEX CONCURRENTLY IF NOT EXISTS organization_unit_tenant_recorded_from_idx
    ON organization_unit (tenant_record_id, recorded_from);
CREATE INDEX CONCURRENTLY IF NOT EXISTS organization_unit_tenant_recorded_to_idx
    ON organization_unit (tenant_record_id, recorded_to)
    WHERE recorded_to IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS organization_unit_version_tenant_recorded_from_idx
    ON organization_unit_version (tenant_record_id, recorded_from);
CREATE INDEX CONCURRENTLY IF NOT EXISTS organization_unit_version_tenant_recorded_to_idx
    ON organization_unit_version (tenant_record_id, recorded_to)
    WHERE recorded_to IS NOT NULL;

CREATE OR REPLACE FUNCTION reject_stale_organization_hierarchy_transaction()
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

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgrelid = 'organization_hierarchy_change_application_record'::regclass
          AND tgname = 'organization_hierarchy_application_concurrency_guard'
          AND NOT tgisinternal
    ) THEN
        CREATE TRIGGER organization_hierarchy_application_concurrency_guard
        BEFORE INSERT ON organization_hierarchy_change_application_record
        FOR EACH ROW
        EXECUTE FUNCTION reject_stale_organization_hierarchy_transaction();
    END IF;
END;
$$;
