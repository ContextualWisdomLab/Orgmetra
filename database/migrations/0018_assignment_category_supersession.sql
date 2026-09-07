-- Persist immutable Assignment category-correction lineage as Orgmetra HRIS truth.
--
-- An Assignment correction is a system-time replacement, never an in-place
-- business rewrite. The predecessor must already be closed at the correction
-- timestamp, the replacement must start at that same timestamp, all business
-- truth except category must be identical, and the two explicit categories must
-- differ. The normalized one-to-one edge prevents unlinked duplicates and forks.

BEGIN;

SET LOCAL search_path = public, pg_catalog;

CREATE TABLE public.assignment_supersession_record (
    tenant_record_id uuid NOT NULL REFERENCES public.tenant_record(tenant_record_id),
    assignment_supersession_record_id uuid PRIMARY KEY,
    predecessor_assignment_record_id uuid NOT NULL,
    replacement_assignment_record_id uuid NOT NULL,
    recorded_at timestamptz NOT NULL,
    CONSTRAINT assignment_supersession_record_id_operational_check
        CHECK (public.is_operational_uuid(assignment_supersession_record_id)),
    CONSTRAINT assignment_supersession_predecessor_id_operational_check
        CHECK (public.is_operational_uuid(predecessor_assignment_record_id)),
    CONSTRAINT assignment_supersession_replacement_id_operational_check
        CHECK (public.is_operational_uuid(replacement_assignment_record_id)),
    CONSTRAINT assignment_supersession_distinct_assignment_check
        CHECK (predecessor_assignment_record_id <> replacement_assignment_record_id),
    CONSTRAINT assignment_supersession_predecessor_tenant_fk
        FOREIGN KEY (tenant_record_id, predecessor_assignment_record_id)
        REFERENCES public.assignment_record(tenant_record_id, assignment_record_id),
    CONSTRAINT assignment_supersession_replacement_tenant_fk
        FOREIGN KEY (tenant_record_id, replacement_assignment_record_id)
        REFERENCES public.assignment_record(tenant_record_id, assignment_record_id),
    CONSTRAINT assignment_supersession_tenant_identity_unique
        UNIQUE (tenant_record_id, assignment_supersession_record_id),
    CONSTRAINT assignment_supersession_predecessor_unique
        UNIQUE (tenant_record_id, predecessor_assignment_record_id),
    CONSTRAINT assignment_supersession_replacement_unique
        UNIQUE (tenant_record_id, replacement_assignment_record_id)
);

CREATE FUNCTION public.enforce_assignment_supersession_link()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
    predecessor_record public.assignment_record%ROWTYPE;
    replacement_record public.assignment_record%ROWTYPE;
BEGIN
    SELECT assignment.*
    INTO predecessor_record
    FROM public.assignment_record AS assignment
    WHERE assignment.tenant_record_id = NEW.tenant_record_id
      AND assignment.assignment_record_id = NEW.predecessor_assignment_record_id
    FOR SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'assignment supersession predecessor does not exist in tenant scope'
            USING ERRCODE = 'foreign_key_violation',
                  CONSTRAINT = 'assignment_supersession_predecessor_tenant_fk',
                  TABLE = 'assignment_supersession_record',
                  SCHEMA = 'public';
    END IF;

    SELECT assignment.*
    INTO replacement_record
    FROM public.assignment_record AS assignment
    WHERE assignment.tenant_record_id = NEW.tenant_record_id
      AND assignment.assignment_record_id = NEW.replacement_assignment_record_id
    FOR SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'assignment supersession replacement does not exist in tenant scope'
            USING ERRCODE = 'foreign_key_violation',
                  CONSTRAINT = 'assignment_supersession_replacement_tenant_fk',
                  TABLE = 'assignment_supersession_record',
                  SCHEMA = 'public';
    END IF;

    IF predecessor_record.recorded_to IS DISTINCT FROM NEW.recorded_at
       OR replacement_record.recorded_from IS DISTINCT FROM NEW.recorded_at
       OR replacement_record.recorded_to IS NOT NULL THEN
        RAISE EXCEPTION 'assignment supersession recorded timestamp must equal predecessor close and replacement start'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'assignment_supersession_recorded_time_check',
                  TABLE = 'assignment_supersession_record',
                  SCHEMA = 'public';
    END IF;

    IF predecessor_record.employment_record_id IS DISTINCT FROM replacement_record.employment_record_id
       OR predecessor_record.person_record_id IS DISTINCT FROM replacement_record.person_record_id
       OR predecessor_record.position_record_id IS DISTINCT FROM replacement_record.position_record_id
       OR predecessor_record.allocation_ratio IS DISTINCT FROM replacement_record.allocation_ratio
       OR predecessor_record.effective_from IS DISTINCT FROM replacement_record.effective_from
       OR predecessor_record.effective_to IS DISTINCT FROM replacement_record.effective_to THEN
        RAISE EXCEPTION 'assignment supersession replacement changed business truth outside category'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'assignment_supersession_business_truth_check',
                  TABLE = 'assignment_supersession_record',
                  SCHEMA = 'public';
    END IF;

    IF predecessor_record.assignment_category_code NOT IN ('primary', 'concurrent_secondary')
       OR replacement_record.assignment_category_code NOT IN ('primary', 'concurrent_secondary')
       OR predecessor_record.assignment_category_code = replacement_record.assignment_category_code THEN
        RAISE EXCEPTION 'assignment supersession must change one explicit assignment category to the other'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'assignment_supersession_category_change_check',
                  TABLE = 'assignment_supersession_record',
                  SCHEMA = 'public';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.enforce_assignment_supersession_link() IS
    'Validates close-to-replacement Assignment category lineage against locked tenant-local HRIS facts.';

CREATE TRIGGER assignment_supersession_link_guard
BEFORE INSERT ON public.assignment_supersession_record
FOR EACH ROW
EXECUTE FUNCTION public.enforce_assignment_supersession_link();

CREATE TRIGGER assignment_supersession_append_only_guard
BEFORE UPDATE OR DELETE ON public.assignment_supersession_record
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

CREATE FUNCTION public.reject_assignment_supersession_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'assignment supersession records cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER assignment_supersession_truncate_guard
BEFORE TRUNCATE ON public.assignment_supersession_record
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_assignment_supersession_truncate();

REVOKE TRUNCATE ON public.assignment_supersession_record FROM PUBLIC;

ALTER TABLE public.assignment_supersession_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assignment_supersession_record FORCE ROW LEVEL SECURITY;
CREATE POLICY assignment_supersession_scope_policy ON public.assignment_supersession_record
USING (tenant_record_id = public.current_tenant_record_id())
WITH CHECK (tenant_record_id = public.current_tenant_record_id());

COMMIT;
