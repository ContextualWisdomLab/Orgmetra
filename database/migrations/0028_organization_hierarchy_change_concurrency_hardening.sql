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
-- A cancelled concurrent build can leave an INVALID same-named index, and a
-- previously misconfigured deployment can leave a VALID same-named index with
-- the wrong table, key order, predicate, or access method. Reconcile either
-- residue rather than trusting the name alone. Exact valid prior work is kept.
WITH expected_index(
    index_name,
    table_name,
    second_column_name,
    expected_predicate
) AS (
    VALUES
        (
            'organization_unit_tenant_recorded_from_idx',
            'organization_unit',
            'recorded_from',
            NULL::text
        ),
        (
            'organization_unit_tenant_recorded_to_idx',
            'organization_unit',
            'recorded_to',
            '(recorded_to IS NOT NULL)'
        ),
        (
            'organization_unit_version_tenant_recorded_from_idx',
            'organization_unit_version',
            'recorded_from',
            NULL::text
        ),
        (
            'organization_unit_version_tenant_recorded_to_idx',
            'organization_unit_version',
            'recorded_to',
            '(recorded_to IS NOT NULL)'
        )
)
SELECT format(
    'DROP INDEX CONCURRENTLY IF EXISTS %I.%I;',
    namespace.nspname,
    index_class.relname
)
FROM expected_index AS expected
JOIN pg_class AS index_class
  ON index_class.relname = expected.index_name
JOIN pg_namespace AS namespace
  ON namespace.oid = index_class.relnamespace
LEFT JOIN pg_index AS index_state
  ON index_state.indexrelid = index_class.oid
LEFT JOIN pg_class AS table_class
  ON table_class.oid = index_state.indrelid
LEFT JOIN pg_am AS access_method
  ON access_method.oid = index_class.relam
WHERE namespace.nspname = 'public'
  AND (
      index_state.indexrelid IS NULL
      OR table_class.relname IS DISTINCT FROM expected.table_name
      OR access_method.amname IS DISTINCT FROM 'btree'
      OR index_state.indisunique
      OR NOT index_state.indisvalid
      OR NOT index_state.indisready
      OR index_state.indnkeyatts <> 2
      OR pg_get_indexdef(index_class.oid, 1, true)
          IS DISTINCT FROM 'tenant_record_id'
      OR pg_get_indexdef(index_class.oid, 2, true)
          IS DISTINCT FROM expected.second_column_name
      OR pg_get_expr(index_state.indpred, index_state.indrelid)
          IS DISTINCT FROM expected.expected_predicate
  )
ORDER BY expected.index_name
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

-- CREATE INDEX IF NOT EXISTS is intentionally not accepted as proof. Assert the
-- full catalog contract after creation so a name collision cannot silently turn
-- a successful migration into an unindexed stale-transaction scan.
DO $$
BEGIN
    IF EXISTS (
        WITH expected_index(
            index_name,
            table_name,
            second_column_name,
            expected_predicate
        ) AS (
            VALUES
                (
                    'organization_unit_tenant_recorded_from_idx',
                    'organization_unit',
                    'recorded_from',
                    NULL::text
                ),
                (
                    'organization_unit_tenant_recorded_to_idx',
                    'organization_unit',
                    'recorded_to',
                    '(recorded_to IS NOT NULL)'
                ),
                (
                    'organization_unit_version_tenant_recorded_from_idx',
                    'organization_unit_version',
                    'recorded_from',
                    NULL::text
                ),
                (
                    'organization_unit_version_tenant_recorded_to_idx',
                    'organization_unit_version',
                    'recorded_to',
                    '(recorded_to IS NOT NULL)'
                )
        )
        SELECT 1
        FROM expected_index AS expected
        LEFT JOIN pg_class AS index_class
          ON index_class.relname = expected.index_name
        LEFT JOIN pg_namespace AS namespace
          ON namespace.oid = index_class.relnamespace
         AND namespace.nspname = 'public'
        LEFT JOIN pg_index AS index_state
          ON index_state.indexrelid = index_class.oid
        LEFT JOIN pg_class AS table_class
          ON table_class.oid = index_state.indrelid
        LEFT JOIN pg_am AS access_method
          ON access_method.oid = index_class.relam
        WHERE namespace.oid IS NULL
           OR index_state.indexrelid IS NULL
           OR table_class.relname IS DISTINCT FROM expected.table_name
           OR access_method.amname IS DISTINCT FROM 'btree'
           OR index_state.indisunique
           OR NOT index_state.indisvalid
           OR NOT index_state.indisready
           OR index_state.indnkeyatts <> 2
           OR pg_get_indexdef(index_class.oid, 1, true)
               IS DISTINCT FROM 'tenant_record_id'
           OR pg_get_indexdef(index_class.oid, 2, true)
               IS DISTINCT FROM expected.second_column_name
           OR pg_get_expr(index_state.indpred, index_state.indrelid)
               IS DISTINCT FROM expected.expected_predicate
    ) THEN
        RAISE EXCEPTION 'organization hierarchy stale-transaction index contract is incomplete'
            USING ERRCODE = '55000';
    END IF;
END;
$$;

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

-- Retry semantics validate the actual trigger contract, not only its name. A
-- disabled or mismatched same-named trigger is replaced; an exact enabled
-- BEFORE INSERT ROW trigger is preserved to keep retries idempotent.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgrelid = 'organization_hierarchy_change_application_record'::regclass
          AND tgname = 'organization_hierarchy_application_concurrency_guard'
          AND NOT tgisinternal
    ) AND NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgrelid = 'organization_hierarchy_change_application_record'::regclass
          AND tgname = 'organization_hierarchy_application_concurrency_guard'
          AND NOT tgisinternal
          AND NOT tgisconstraint
          AND tgenabled = 'O'
          AND tgtype = 7
          AND tgfoid = 'reject_stale_organization_hierarchy_transaction()'::regprocedure
    ) THEN
        DROP TRIGGER organization_hierarchy_application_concurrency_guard
            ON organization_hierarchy_change_application_record;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgrelid = 'organization_hierarchy_change_application_record'::regclass
          AND tgname = 'organization_hierarchy_application_concurrency_guard'
          AND NOT tgisinternal
          AND NOT tgisconstraint
          AND tgenabled = 'O'
          AND tgtype = 7
          AND tgfoid = 'reject_stale_organization_hierarchy_transaction()'::regprocedure
    ) THEN
        CREATE TRIGGER organization_hierarchy_application_concurrency_guard
        BEFORE INSERT ON organization_hierarchy_change_application_record
        FOR EACH ROW
        EXECUTE FUNCTION reject_stale_organization_hierarchy_transaction();
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgrelid = 'organization_hierarchy_change_application_record'::regclass
          AND tgname = 'organization_hierarchy_application_concurrency_guard'
          AND NOT tgisinternal
          AND NOT tgisconstraint
          AND tgenabled = 'O'
          AND tgtype = 7
          AND tgfoid = 'reject_stale_organization_hierarchy_transaction()'::regprocedure
    ) THEN
        RAISE EXCEPTION 'organization hierarchy stale-transaction trigger contract is incomplete'
            USING ERRCODE = '55000';
    END IF;
END;
$$;
