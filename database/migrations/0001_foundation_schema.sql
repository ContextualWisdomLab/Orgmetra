-- Orgmetra foundation schema.
-- Every owned object uses descriptive two-or-more-word snake_case names.

CREATE TABLE person_record (
    person_record_id uuid PRIMARY KEY,
    display_name text NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz
);

CREATE TABLE employment_record (
    employment_record_id uuid PRIMARY KEY,
    person_record_id uuid NOT NULL REFERENCES person_record(person_record_id),
    employment_status_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz
);

CREATE TABLE organization_unit (
    organization_unit_id uuid PRIMARY KEY,
    unit_name text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz
);

CREATE TABLE job_profile (
    job_profile_id uuid PRIMARY KEY,
    job_title text NOT NULL,
    job_version_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz
);

CREATE TABLE position_record (
    position_record_id uuid PRIMARY KEY,
    organization_unit_id uuid NOT NULL REFERENCES organization_unit(organization_unit_id),
    job_profile_id uuid NOT NULL REFERENCES job_profile(job_profile_id),
    position_status_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz
);

CREATE TABLE assignment_record (
    assignment_record_id uuid PRIMARY KEY,
    person_record_id uuid NOT NULL REFERENCES person_record(person_record_id),
    position_record_id uuid NOT NULL REFERENCES position_record(position_record_id),
    allocation_ratio numeric(5,4) NOT NULL CHECK (allocation_ratio > 0 AND allocation_ratio <= 1),
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz
);

CREATE TABLE candidate_profile (
    candidate_profile_id uuid PRIMARY KEY,
    application_status_code text NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz
);

CREATE TABLE candidate_worker_link (
    candidate_worker_link_id uuid PRIMARY KEY,
    candidate_profile_id uuid NOT NULL UNIQUE REFERENCES candidate_profile(candidate_profile_id),
    person_record_id uuid NOT NULL REFERENCES person_record(person_record_id),
    linked_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE criterion_blueprint (
    criterion_blueprint_id uuid PRIMARY KEY,
    job_profile_id uuid NOT NULL REFERENCES job_profile(job_profile_id),
    criterion_type_code text NOT NULL,
    criterion_version_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz
);

CREATE TABLE criterion_observation (
    criterion_observation_id uuid PRIMARY KEY,
    criterion_blueprint_id uuid NOT NULL REFERENCES criterion_blueprint(criterion_blueprint_id),
    person_record_id uuid NOT NULL REFERENCES person_record(person_record_id),
    observed_value numeric NOT NULL,
    observed_at timestamptz NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz
);

CREATE TABLE selection_decision (
    selection_decision_id uuid PRIMARY KEY,
    candidate_profile_id uuid NOT NULL REFERENCES candidate_profile(candidate_profile_id),
    job_profile_id uuid NOT NULL REFERENCES job_profile(job_profile_id),
    decision_code text NOT NULL,
    decided_at timestamptz NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz
);

CREATE TABLE validity_study (
    validity_study_id uuid PRIMARY KEY,
    criterion_blueprint_id uuid NOT NULL REFERENCES criterion_blueprint(criterion_blueprint_id),
    study_status_code text NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz
);

CREATE TABLE compensation_record (
    compensation_record_id uuid PRIMARY KEY,
    person_record_id uuid NOT NULL REFERENCES person_record(person_record_id),
    amount_value numeric NOT NULL,
    currency_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz
);

CREATE TABLE employment_transition (
    employment_transition_id uuid PRIMARY KEY,
    employment_record_id uuid NOT NULL REFERENCES employment_record(employment_record_id),
    transition_type_code text NOT NULL,
    effective_date date NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz
);
