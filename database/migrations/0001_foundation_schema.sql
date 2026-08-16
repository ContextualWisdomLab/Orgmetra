-- Orgmetra foundation schema.
-- Every owned object uses descriptive two-or-more-word snake_case names.
-- This baseline keeps tables unqualified while the modular deployment assigns
-- them to the service-owned schemas and roles defined in ARCHITECTURE.md.

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE person_record (
    person_record_id uuid PRIMARY KEY,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT person_record_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE TABLE person_name_record (
    person_name_record_id uuid PRIMARY KEY,
    person_record_id uuid NOT NULL REFERENCES person_record(person_record_id),
    display_name text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT person_name_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT person_name_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT person_name_bitemporal_exclusion
        EXCLUDE USING gist (
            person_record_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE TABLE employment_record (
    employment_record_id uuid PRIMARY KEY,
    person_record_id uuid NOT NULL REFERENCES person_record(person_record_id),
    employment_status_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT employment_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT employment_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE TABLE organization_unit (
    organization_unit_id uuid PRIMARY KEY,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT organization_unit_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE TABLE organization_unit_version (
    organization_unit_version_id uuid PRIMARY KEY,
    organization_unit_id uuid NOT NULL REFERENCES organization_unit(organization_unit_id),
    unit_name text NOT NULL,
    organization_type_code text NOT NULL,
    parent_organization_unit_id uuid REFERENCES organization_unit(organization_unit_id),
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT organization_unit_parent_not_self_check
        CHECK (parent_organization_unit_id IS NULL OR parent_organization_unit_id <> organization_unit_id),
    CONSTRAINT organization_unit_version_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT organization_unit_version_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT organization_unit_bitemporal_exclusion
        EXCLUDE USING gist (
            organization_unit_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE TABLE job_profile (
    job_profile_id uuid PRIMARY KEY,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT job_profile_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE TABLE job_profile_version (
    job_profile_version_id uuid PRIMARY KEY,
    job_profile_id uuid NOT NULL REFERENCES job_profile(job_profile_id),
    job_title text NOT NULL,
    job_family_code text NOT NULL,
    job_version_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT job_profile_version_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT job_profile_version_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT job_profile_bitemporal_exclusion
        EXCLUDE USING gist (
            job_profile_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE TABLE position_record (
    position_record_id uuid PRIMARY KEY,
    organization_unit_id uuid NOT NULL REFERENCES organization_unit(organization_unit_id),
    job_profile_id uuid NOT NULL REFERENCES job_profile(job_profile_id),
    position_status_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT position_record_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT position_record_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE TABLE assignment_record (
    assignment_record_id uuid PRIMARY KEY,
    person_record_id uuid NOT NULL REFERENCES person_record(person_record_id),
    position_record_id uuid NOT NULL REFERENCES position_record(position_record_id),
    allocation_ratio numeric(5,4) NOT NULL
        CONSTRAINT assignment_allocation_ratio_check
        CHECK (allocation_ratio > 0 AND allocation_ratio <= 1),
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT assignment_record_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT assignment_record_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE TABLE candidate_profile (
    candidate_profile_id uuid PRIMARY KEY,
    application_status_code text NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT candidate_profile_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE TABLE candidate_worker_link (
    candidate_worker_link_id uuid PRIMARY KEY,
    candidate_profile_id uuid NOT NULL UNIQUE REFERENCES candidate_profile(candidate_profile_id),
    person_record_id uuid NOT NULL REFERENCES person_record(person_record_id),
    linked_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE performance_cycle (
    performance_cycle_id uuid PRIMARY KEY,
    cycle_name text NOT NULL,
    cycle_status_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT performance_cycle_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT performance_cycle_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE TABLE criterion_blueprint (
    criterion_blueprint_id uuid PRIMARY KEY,
    job_profile_id uuid NOT NULL REFERENCES job_profile(job_profile_id),
    criterion_type_code text NOT NULL,
    criterion_version_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT criterion_blueprint_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT criterion_blueprint_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE TABLE criterion_observation (
    criterion_observation_id uuid PRIMARY KEY,
    criterion_blueprint_id uuid NOT NULL REFERENCES criterion_blueprint(criterion_blueprint_id),
    performance_cycle_id uuid NOT NULL REFERENCES performance_cycle(performance_cycle_id),
    person_record_id uuid NOT NULL REFERENCES person_record(person_record_id),
    observed_value numeric NOT NULL,
    observed_at timestamptz NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT criterion_observation_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE TABLE selection_decision (
    selection_decision_id uuid PRIMARY KEY,
    candidate_profile_id uuid NOT NULL REFERENCES candidate_profile(candidate_profile_id),
    job_profile_id uuid NOT NULL REFERENCES job_profile(job_profile_id),
    tenant_reference text NOT NULL,
    actor_reference text NOT NULL,
    purpose_code text NOT NULL,
    decision_code text NOT NULL,
    decision_reason text NOT NULL,
    confirmation_reference text NOT NULL,
    decided_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE selection_decision_evidence (
    selection_decision_evidence_id uuid PRIMARY KEY,
    selection_decision_id uuid NOT NULL REFERENCES selection_decision(selection_decision_id),
    evidence_reference text NOT NULL,
    evidence_version_code text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT selection_decision_evidence_unique
        UNIQUE (selection_decision_id, evidence_reference, evidence_version_code)
);

CREATE TABLE validity_study (
    validity_study_id uuid PRIMARY KEY,
    criterion_blueprint_id uuid NOT NULL REFERENCES criterion_blueprint(criterion_blueprint_id),
    study_status_code text NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT validity_study_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE TABLE compensation_record (
    compensation_record_id uuid PRIMARY KEY,
    person_record_id uuid NOT NULL REFERENCES person_record(person_record_id),
    amount_value numeric NOT NULL,
    currency_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT compensation_record_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT compensation_record_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE TABLE employment_transition (
    employment_transition_id uuid PRIMARY KEY,
    employment_record_id uuid NOT NULL REFERENCES employment_record(employment_record_id),
    transition_type_code text NOT NULL,
    effective_date date NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT employment_transition_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE FUNCTION protect_bitemporal_history()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'bitemporal fact cannot be deleted'
            USING ERRCODE = '55000';
    END IF;

    IF OLD.recorded_to IS NOT NULL
       OR NEW.recorded_to IS NULL
       OR NEW.recorded_to <= OLD.recorded_from
       OR to_jsonb(NEW) - 'recorded_to' <> to_jsonb(OLD) - 'recorded_to' THEN
        RAISE EXCEPTION 'bitemporal correction may only close an open recorded interval'
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER person_name_bitemporal_guard
BEFORE UPDATE OR DELETE ON person_name_record
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER organization_unit_bitemporal_guard
BEFORE UPDATE OR DELETE ON organization_unit_version
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER job_profile_bitemporal_guard
BEFORE UPDATE OR DELETE ON job_profile_version
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE FUNCTION reject_append_only_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'append-only relation cannot be updated or deleted'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER candidate_worker_link_append_only_guard
BEFORE UPDATE OR DELETE ON candidate_worker_link
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER selection_decision_append_only_guard
BEFORE UPDATE OR DELETE ON selection_decision
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER selection_decision_evidence_append_only_guard
BEFORE UPDATE OR DELETE ON selection_decision_evidence
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();
