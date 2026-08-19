-- Repair validity-study membership so one analytic case cannot mix unrelated
-- decisions, evidence sets, criterion outcomes, or workers.
--
-- The original three independent link tables remain readable for historical
-- compatibility, but new writes and table-wide destruction are closed. New study
-- membership must use one normalized validity_study_case_record that binds the
-- exact hire decision, its sealed evidence set, the governed candidate->worker
-- conversion, and the criterion observation for that same worker and study criterion.

BEGIN;

SET LOCAL search_path = public, pg_catalog;

CREATE FUNCTION public.reject_legacy_validity_study_link_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'legacy validity-study links are read-only; use validity_study_case_record'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER validity_study_decision_legacy_insert_guard
BEFORE INSERT ON validity_study_decision_link
FOR EACH ROW
EXECUTE FUNCTION public.reject_legacy_validity_study_link_insert();

CREATE TRIGGER validity_study_outcome_legacy_insert_guard
BEFORE INSERT ON validity_study_outcome_link
FOR EACH ROW
EXECUTE FUNCTION public.reject_legacy_validity_study_link_insert();

CREATE TRIGGER validity_study_evidence_legacy_insert_guard
BEFORE INSERT ON validity_study_evidence_set_link
FOR EACH ROW
EXECUTE FUNCTION public.reject_legacy_validity_study_link_insert();

CREATE FUNCTION public.reject_legacy_validity_study_link_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'legacy validity-study links are read-only; use validity_study_case_record'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER validity_study_decision_legacy_truncate_guard
BEFORE TRUNCATE ON validity_study_decision_link
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_legacy_validity_study_link_truncate();

CREATE TRIGGER validity_study_outcome_legacy_truncate_guard
BEFORE TRUNCATE ON validity_study_outcome_link
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_legacy_validity_study_link_truncate();

CREATE TRIGGER validity_study_evidence_legacy_truncate_guard
BEFORE TRUNCATE ON validity_study_evidence_set_link
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_legacy_validity_study_link_truncate();

REVOKE TRUNCATE ON validity_study_decision_link FROM PUBLIC;
REVOKE TRUNCATE ON validity_study_outcome_link FROM PUBLIC;
REVOKE TRUNCATE ON validity_study_evidence_set_link FROM PUBLIC;

CREATE TABLE validity_study_case_record (
    tenant_record_id uuid NOT NULL REFERENCES public.tenant_record(tenant_record_id),
    validity_study_case_record_id uuid PRIMARY KEY,
    validity_study_id uuid NOT NULL,
    selection_decision_id uuid NOT NULL,
    decision_evidence_set_id uuid NOT NULL,
    criterion_observation_id uuid NOT NULL,
    candidate_worker_conversion_record_id uuid NOT NULL,
    linked_at timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    CONSTRAINT validity_case_record_id_operational_check
        CHECK (public.is_operational_uuid(validity_study_case_record_id)),
    CONSTRAINT validity_case_study_tenant_fk
        FOREIGN KEY (tenant_record_id, validity_study_id)
        REFERENCES public.validity_study(tenant_record_id, validity_study_id),
    CONSTRAINT validity_case_decision_tenant_fk
        FOREIGN KEY (tenant_record_id, selection_decision_id)
        REFERENCES public.selection_decision(tenant_record_id, selection_decision_id),
    CONSTRAINT validity_case_evidence_set_tenant_fk
        FOREIGN KEY (tenant_record_id, decision_evidence_set_id)
        REFERENCES public.decision_evidence_set(tenant_record_id, decision_evidence_set_id),
    CONSTRAINT validity_case_observation_tenant_fk
        FOREIGN KEY (tenant_record_id, criterion_observation_id)
        REFERENCES public.criterion_observation(tenant_record_id, criterion_observation_id),
    CONSTRAINT validity_case_conversion_tenant_fk
        FOREIGN KEY (tenant_record_id, candidate_worker_conversion_record_id)
        REFERENCES public.candidate_worker_conversion_record(
            tenant_record_id, candidate_worker_conversion_record_id
        ),
    CONSTRAINT validity_case_tenant_identity_unique
        UNIQUE (tenant_record_id, validity_study_case_record_id),
    CONSTRAINT validity_case_study_decision_unique
        UNIQUE (tenant_record_id, validity_study_id, selection_decision_id),
    CONSTRAINT validity_case_study_outcome_unique
        UNIQUE (tenant_record_id, validity_study_id, criterion_observation_id)
);

CREATE FUNCTION public.validate_validity_study_case()
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
    FROM public.validity_study AS study
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

CREATE TRIGGER validity_study_case_governance_guard
BEFORE INSERT ON validity_study_case_record
FOR EACH ROW
EXECUTE FUNCTION public.validate_validity_study_case();

CREATE TRIGGER validity_study_case_append_only_guard
BEFORE UPDATE OR DELETE ON validity_study_case_record
FOR EACH ROW
EXECUTE FUNCTION public.reject_append_only_mutation();

CREATE FUNCTION public.reject_validity_study_case_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'validity-study case history cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER validity_study_case_truncate_guard
BEFORE TRUNCATE ON validity_study_case_record
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_validity_study_case_truncate();

REVOKE TRUNCATE ON validity_study_case_record FROM PUBLIC;

ALTER TABLE validity_study_case_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE validity_study_case_record FORCE ROW LEVEL SECURITY;
CREATE POLICY validity_study_case_scope_policy ON validity_study_case_record
USING (tenant_record_id = public.current_tenant_record_id())
WITH CHECK (tenant_record_id = public.current_tenant_record_id());

COMMIT;