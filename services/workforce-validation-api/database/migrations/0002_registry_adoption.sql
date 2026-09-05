-- Adopt the existing validity-study registry into its canonical bounded-context schema.
-- ALTER TABLE ... SET SCHEMA preserves the relation OID, rows, constraints, indexes,
-- RLS policy and bitemporal trigger instead of copying authoritative HR evidence.

BEGIN;

CREATE ROLE workforce_validation_runtime_role NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS;

ALTER TABLE public.validity_study SET SCHEMA workforce_validation;
ALTER TABLE workforce_validation.validity_study OWNER TO workforce_validation_role;

-- The protected validity-study case trigger predates owner-schema adoption and its
-- PL/pgSQL body names public.validity_study explicitly. ALTER TABLE ... SET SCHEMA
-- preserves the trigger/function objects but cannot rewrite relation names embedded
-- in function source. Replace the existing function in place so normalized case
-- governance continues to read the same registry relation after ownership moves.
CREATE OR REPLACE FUNCTION public.validate_validity_study_case()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    study_criterion_id uuid;
    study_recorded_from timestamptz;
    study_recorded_to timestamptz;
    criterion_job_id uuid;
    decision_candidate_id uuid;
    decision_job_id uuid;
    decision_evidence_id uuid;
    decision_recorded_at timestamptz;
    evidence_sealed_at timestamptz;
    evidence_sealed_decision_id uuid;
    outcome_criterion_id uuid;
    outcome_person_id uuid;
    outcome_recorded_from timestamptz;
    outcome_recorded_to timestamptz;
    conversion_candidate_id uuid;
    conversion_person_id uuid;
    conversion_decision_id uuid;
    conversion_recorded_from timestamptz;
    conversion_recorded_to timestamptz;
BEGIN
    SELECT
        study.criterion_blueprint_id,
        study.recorded_from,
        study.recorded_to,
        criterion.job_profile_id
    INTO
        study_criterion_id,
        study_recorded_from,
        study_recorded_to,
        criterion_job_id
    FROM workforce_validation.validity_study AS study
    JOIN public.criterion_blueprint AS criterion
      ON criterion.tenant_record_id = study.tenant_record_id
     AND criterion.criterion_blueprint_id = study.criterion_blueprint_id
    WHERE study.tenant_record_id = NEW.tenant_record_id
      AND study.validity_study_id = NEW.validity_study_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'validity-study case requires a tenant-local study and criterion'
            USING ERRCODE = '23503';
    END IF;

    IF NEW.linked_at < study_recorded_from
       OR (study_recorded_to IS NOT NULL AND NEW.linked_at >= study_recorded_to) THEN
        RAISE EXCEPTION 'validity-study case must bind a study version visible at linked_at'
            USING ERRCODE = '23514';
    END IF;

    SELECT
        decision.candidate_profile_id,
        decision.job_profile_id,
        decision.decision_evidence_set_id,
        decision.recorded_at
    INTO
        decision_candidate_id,
        decision_job_id,
        decision_evidence_id,
        decision_recorded_at
    FROM public.selection_decision AS decision
    WHERE decision.tenant_record_id = NEW.tenant_record_id
      AND decision.selection_decision_id = NEW.selection_decision_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'validity-study case requires a tenant-local selection decision'
            USING ERRCODE = '23503';
    END IF;

    IF decision_job_id IS DISTINCT FROM criterion_job_id THEN
        RAISE EXCEPTION 'validity-study case decision belongs to a different Job'
            USING ERRCODE = '23514';
    END IF;

    IF decision_evidence_id IS DISTINCT FROM NEW.decision_evidence_set_id THEN
        RAISE EXCEPTION 'validity-study case requires the selection decision''s exact evidence set'
            USING ERRCODE = '23514';
    END IF;

    SELECT evidence.sealed_at, evidence.sealed_selection_decision_id
    INTO evidence_sealed_at, evidence_sealed_decision_id
    FROM public.decision_evidence_set AS evidence
    WHERE evidence.tenant_record_id = NEW.tenant_record_id
      AND evidence.decision_evidence_set_id = NEW.decision_evidence_set_id;

    IF NOT FOUND
       OR evidence_sealed_at IS NULL
       OR evidence_sealed_decision_id IS DISTINCT FROM NEW.selection_decision_id THEN
        RAISE EXCEPTION 'validity-study case requires evidence sealed by the exact selection decision'
            USING ERRCODE = '23514';
    END IF;

    SELECT
        observation.criterion_blueprint_id,
        observation.person_record_id,
        observation.recorded_from,
        observation.recorded_to
    INTO
        outcome_criterion_id,
        outcome_person_id,
        outcome_recorded_from,
        outcome_recorded_to
    FROM public.criterion_observation AS observation
    WHERE observation.tenant_record_id = NEW.tenant_record_id
      AND observation.criterion_observation_id = NEW.criterion_observation_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'validity-study case requires a tenant-local criterion observation'
            USING ERRCODE = '23503';
    END IF;

    IF outcome_criterion_id IS DISTINCT FROM study_criterion_id THEN
        RAISE EXCEPTION 'validity-study case outcome uses a different criterion'
            USING ERRCODE = '23514';
    END IF;

    SELECT
        conversion.candidate_profile_id,
        conversion.person_record_id,
        conversion.selection_decision_id,
        conversion.recorded_from,
        conversion.recorded_to
    INTO
        conversion_candidate_id,
        conversion_person_id,
        conversion_decision_id,
        conversion_recorded_from,
        conversion_recorded_to
    FROM public.candidate_worker_conversion_record AS conversion
    WHERE conversion.tenant_record_id = NEW.tenant_record_id
      AND conversion.candidate_worker_conversion_record_id =
          NEW.candidate_worker_conversion_record_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'validity-study case requires a governed candidate-worker conversion'
            USING ERRCODE = '23503';
    END IF;

    IF conversion_decision_id IS DISTINCT FROM NEW.selection_decision_id
       OR conversion_candidate_id IS DISTINCT FROM decision_candidate_id THEN
        RAISE EXCEPTION 'validity-study case conversion does not bind the selected candidate'
            USING ERRCODE = '23514';
    END IF;

    IF conversion_person_id IS DISTINCT FROM outcome_person_id THEN
        RAISE EXCEPTION 'validity-study case outcome belongs to a different worker'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.linked_at < decision_recorded_at
       OR NEW.linked_at < evidence_sealed_at
       OR NEW.linked_at < outcome_recorded_from
       OR (
            outcome_recorded_to IS NOT NULL
            AND NEW.linked_at >= outcome_recorded_to
       )
       OR NEW.linked_at < conversion_recorded_from
       OR (
            conversion_recorded_to IS NOT NULL
            AND NEW.linked_at >= conversion_recorded_to
       ) THEN
        RAISE EXCEPTION 'validity-study case may use only evidence visible at linked_at'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

REVOKE ALL ON TABLE workforce_validation.validity_study FROM PUBLIC;
GRANT USAGE ON SCHEMA workforce_validation TO workforce_validation_runtime_role;
GRANT SELECT ON TABLE workforce_validation.validity_study TO workforce_validation_runtime_role;
GRANT EXECUTE ON FUNCTION public.current_tenant_record_id() TO workforce_validation_runtime_role;

COMMIT;
