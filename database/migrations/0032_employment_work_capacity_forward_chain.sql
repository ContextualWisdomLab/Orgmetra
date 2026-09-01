-- Prevent a later-recorded work-capacity application from inserting a business-
-- effective point before an already-authoritative later point. Without this guard,
-- a retroactive point could invalidate the reviewed current-capacity premise of a
-- previously persisted future change. Retroactive corrections require a separate
-- replay/revalidation boundary that can re-prove every downstream effective point.

CREATE FUNCTION enforce_employment_work_capacity_forward_chain()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    insertion_time timestamptz := pg_catalog.transaction_timestamp();
    anchor_employment_id uuid;
    latest_effective_on date;
BEGIN
    SELECT capacity_record.employment_record_id
    INTO anchor_employment_id
    FROM employment_work_capacity_record AS capacity_record
    WHERE capacity_record.tenant_record_id = NEW.tenant_record_id
      AND capacity_record.employment_work_capacity_record_id =
          NEW.employment_work_capacity_record_id;

    IF anchor_employment_id IS NULL THEN
        RETURN NEW;
    END IF;

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(
            NEW.tenant_record_id::text || ':' || anchor_employment_id::text,
            0
        )
    );

    SELECT max(capacity_version.effective_on)
    INTO latest_effective_on
    FROM employment_work_capacity_version AS capacity_version
    WHERE capacity_version.tenant_record_id = NEW.tenant_record_id
      AND capacity_version.employment_work_capacity_record_id =
          NEW.employment_work_capacity_record_id
      AND capacity_version.recorded_from <= insertion_time
      AND (
          capacity_version.recorded_to IS NULL
          OR capacity_version.recorded_to > insertion_time
      );

    IF latest_effective_on IS NOT NULL AND NEW.effective_on <= latest_effective_on THEN
        RAISE EXCEPTION 'retroactive capacity changes require a dedicated correction/replay boundary'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION enforce_employment_work_capacity_forward_chain() IS
    'Serializes one Employment capacity chain and permits normal applications only after the latest currently authoritative effective point; retroactive corrections need downstream replay/revalidation.';

CREATE TRIGGER employment_work_capacity_forward_chain_guard
BEFORE INSERT ON employment_work_capacity_version
FOR EACH ROW
EXECUTE FUNCTION enforce_employment_work_capacity_forward_chain();

REVOKE ALL ON FUNCTION enforce_employment_work_capacity_forward_chain() FROM PUBLIC;
