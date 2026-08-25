-- Normalize recruiting applications away from candidate_profile.
--
-- candidate_profile is a durable candidate identity and cannot safely carry one
-- application status when the same candidate pursues multiple openings. This
-- migration adds a durable candidate application anchor plus bitemporal workflow
-- stage history. Candidate-specific terminal outcomes remain outside this raw
-- workflow stage vocabulary until their authoritative decision/withdrawal evidence
-- can be proven at a governed boundary.

BEGIN;

SET LOCAL search_path = public, pg_catalog;

-- A Position is already a durable Job-bound seat. Publishing the composite
-- identity lets candidate_application_record prove, with a foreign key rather
-- than duplicated application logic, that an optional seat belongs to the Job
-- being pursued.
ALTER TABLE public.position_record
ADD CONSTRAINT position_record_tenant_position_job_unique
UNIQUE (tenant_record_id, position_record_id, job_profile_id);

-- Table creation stays search-path-qualified rather than schema-qualified because
-- the repository foundation validator applies the same descriptive two-word
-- snake_case rule to an explicit schema token. SET LOCAL search_path above keeps
-- these objects owned by public without weakening that repository-wide check.
CREATE TABLE candidate_application_record (
    tenant_record_id uuid NOT NULL REFERENCES public.tenant_record(tenant_record_id),
    candidate_application_record_id uuid PRIMARY KEY,
    candidate_profile_id uuid NOT NULL,
    job_profile_id uuid NOT NULL,
    position_record_id uuid,
    requisition_reference text NOT NULL,
    submitted_at timestamptz NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    recorded_to timestamptz,
    CONSTRAINT candidate_application_record_id_operational_check
        CHECK (
            candidate_application_record_id <> '00000000-0000-0000-0000-000000000000'::uuid
            AND candidate_application_record_id <> 'ffffffff-ffff-ffff-ffff-ffffffffffff'::uuid
        ),
    CONSTRAINT candidate_application_candidate_tenant_fk
        FOREIGN KEY (tenant_record_id, candidate_profile_id)
        REFERENCES public.candidate_profile(tenant_record_id, candidate_profile_id),
    CONSTRAINT candidate_application_job_tenant_fk
        FOREIGN KEY (tenant_record_id, job_profile_id)
        REFERENCES public.job_profile(tenant_record_id, job_profile_id),
    CONSTRAINT candidate_application_position_job_tenant_fk
        FOREIGN KEY (tenant_record_id, position_record_id, job_profile_id)
        REFERENCES public.position_record(
            tenant_record_id, position_record_id, job_profile_id
        ),
    CONSTRAINT candidate_application_requisition_reference_check
        CHECK (
            requisition_reference ~
                '^requisition:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            AND pg_catalog.split_part(requisition_reference, ':', 2)
                <> '00000000-0000-0000-0000-000000000000'
            AND pg_catalog.split_part(requisition_reference, ':', 2)
                <> 'ffffffff-ffff-ffff-ffff-ffffffffffff'
        ),
    CONSTRAINT candidate_application_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT candidate_application_submission_recorded_order_check
        CHECK (submitted_at <= recorded_from),
    CONSTRAINT candidate_application_tenant_identity_unique
        UNIQUE (tenant_record_id, candidate_application_record_id),
    CONSTRAINT candidate_application_candidate_requisition_unique
        UNIQUE (tenant_record_id, candidate_profile_id, requisition_reference)
);

CREATE TABLE candidate_application_stage_record (
    tenant_record_id uuid NOT NULL REFERENCES public.tenant_record(tenant_record_id),
    candidate_application_stage_record_id uuid PRIMARY KEY,
    candidate_application_record_id uuid NOT NULL,
    application_stage_code text NOT NULL,
    effective_from timestamptz NOT NULL,
    effective_to timestamptz,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    recorded_to timestamptz,
    CONSTRAINT candidate_application_stage_record_id_operational_check
        CHECK (
            candidate_application_stage_record_id
                <> '00000000-0000-0000-0000-000000000000'::uuid
            AND candidate_application_stage_record_id
                <> 'ffffffff-ffff-ffff-ffff-ffffffffffff'::uuid
        ),
    CONSTRAINT candidate_application_stage_application_tenant_fk
        FOREIGN KEY (tenant_record_id, candidate_application_record_id)
        REFERENCES public.candidate_application_record(
            tenant_record_id, candidate_application_record_id
        ),
    CONSTRAINT candidate_application_stage_code_check
        CHECK (
            application_stage_code IN (
                'received',
                'screening',
                'assessment',
                'interview',
                'offer_pending'
            )
        ),
    CONSTRAINT candidate_application_stage_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT candidate_application_stage_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT candidate_application_stage_tenant_identity_unique
        UNIQUE (tenant_record_id, candidate_application_stage_record_id),
    CONSTRAINT candidate_application_stage_bitemporal_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            candidate_application_record_id WITH =,
            tstzrange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE FUNCTION public.validate_candidate_application_stage()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    application_submitted_at timestamptz;
BEGIN
    SELECT application_record.submitted_at
    INTO application_submitted_at
    FROM public.candidate_application_record AS application_record
    WHERE application_record.tenant_record_id = NEW.tenant_record_id
      AND application_record.candidate_application_record_id =
          NEW.candidate_application_record_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'candidate application stage requires a tenant-local application'
            USING ERRCODE = '23503';
    END IF;

    IF NEW.effective_from < application_submitted_at THEN
        RAISE EXCEPTION 'candidate application stage cannot predate application submission'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER candidate_application_stage_scope_guard
BEFORE INSERT OR UPDATE ON public.candidate_application_stage_record
FOR EACH ROW
EXECUTE FUNCTION public.validate_candidate_application_stage();

CREATE TRIGGER candidate_application_bitemporal_guard
BEFORE UPDATE OR DELETE ON public.candidate_application_record
FOR EACH ROW
EXECUTE FUNCTION public.protect_bitemporal_history();

CREATE TRIGGER candidate_application_stage_bitemporal_guard
BEFORE UPDATE OR DELETE ON public.candidate_application_stage_record
FOR EACH ROW
EXECUTE FUNCTION public.protect_bitemporal_history();

CREATE FUNCTION public.reject_candidate_application_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'candidate application history cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER candidate_application_truncate_guard
BEFORE TRUNCATE ON public.candidate_application_record
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_candidate_application_truncate();

CREATE TRIGGER candidate_application_stage_truncate_guard
BEFORE TRUNCATE ON public.candidate_application_stage_record
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_candidate_application_truncate();

REVOKE TRUNCATE ON public.candidate_application_record FROM PUBLIC;
REVOKE TRUNCATE ON public.candidate_application_stage_record FROM PUBLIC;

-- Keep these FORCE statements unqualified after SET LOCAL search_path so the
-- repository's foundation validator can independently discover every tenant
-- table's forced-RLS contract by owned relation name.
ALTER TABLE candidate_application_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_application_record FORCE ROW LEVEL SECURITY;
CREATE POLICY candidate_application_scope_policy ON public.candidate_application_record
USING (tenant_record_id = public.current_tenant_record_id())
WITH CHECK (tenant_record_id = public.current_tenant_record_id());

ALTER TABLE candidate_application_stage_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_application_stage_record FORCE ROW LEVEL SECURITY;
CREATE POLICY candidate_application_stage_scope_policy
ON public.candidate_application_stage_record
USING (tenant_record_id = public.current_tenant_record_id())
WITH CHECK (tenant_record_id = public.current_tenant_record_id());

COMMENT ON COLUMN public.candidate_profile.application_status_code IS
    'Legacy unscoped recruiting status retained for compatibility; canonical new workflow state belongs to candidate_application_stage_record.';

COMMIT;
