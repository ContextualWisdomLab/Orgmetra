-- Orgmetra foundation schema.
-- Every owned object uses descriptive two-or-more-word snake_case names.
-- This baseline keeps tables unqualified while the modular deployment assigns
-- them to the service-owned schemas and roles defined in ARCHITECTURE.md.

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE tenant_record (
    tenant_record_id uuid PRIMARY KEY,
    tenant_reference text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE person_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    person_record_id uuid PRIMARY KEY,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT person_record_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT person_record_tenant_identity_unique
        UNIQUE (tenant_record_id, person_record_id)
);

CREATE TABLE person_name_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    person_name_record_id uuid PRIMARY KEY,
    person_record_id uuid NOT NULL,
    display_name text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT person_name_person_tenant_fk
        FOREIGN KEY (tenant_record_id, person_record_id)
        REFERENCES person_record(tenant_record_id, person_record_id),
    CONSTRAINT person_name_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT person_name_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT person_name_bitemporal_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            person_record_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE TABLE employment_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    employment_record_id uuid PRIMARY KEY,
    person_record_id uuid NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT employment_person_tenant_fk
        FOREIGN KEY (tenant_record_id, person_record_id)
        REFERENCES person_record(tenant_record_id, person_record_id),
    CONSTRAINT employment_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT employment_record_tenant_identity_unique
        UNIQUE (tenant_record_id, employment_record_id),
    CONSTRAINT employment_record_tenant_person_unique
        UNIQUE (tenant_record_id, employment_record_id, person_record_id)
);

CREATE TABLE employment_record_version (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    employment_record_version_id uuid PRIMARY KEY,
    employment_record_id uuid NOT NULL,
    employment_status_code text NOT NULL,
    employment_concurrency_code text NOT NULL DEFAULT 'exclusive'
        CONSTRAINT employment_concurrency_code_check
        CHECK (employment_concurrency_code IN ('exclusive', 'concurrent')),
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT employment_version_record_tenant_fk
        FOREIGN KEY (tenant_record_id, employment_record_id)
        REFERENCES employment_record(tenant_record_id, employment_record_id),
    CONSTRAINT employment_version_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT employment_version_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT employment_record_bitemporal_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            employment_record_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE TABLE organization_unit (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    organization_unit_id uuid PRIMARY KEY,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT organization_unit_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT organization_unit_tenant_identity_unique
        UNIQUE (tenant_record_id, organization_unit_id)
);

CREATE TABLE organization_unit_version (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    organization_unit_version_id uuid PRIMARY KEY,
    organization_unit_id uuid NOT NULL,
    unit_name text NOT NULL,
    organization_type_code text NOT NULL,
    parent_organization_unit_id uuid,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT organization_version_unit_tenant_fk
        FOREIGN KEY (tenant_record_id, organization_unit_id)
        REFERENCES organization_unit(tenant_record_id, organization_unit_id),
    CONSTRAINT organization_version_parent_tenant_fk
        FOREIGN KEY (tenant_record_id, parent_organization_unit_id)
        REFERENCES organization_unit(tenant_record_id, organization_unit_id),
    CONSTRAINT organization_unit_parent_not_self_check
        CHECK (parent_organization_unit_id IS NULL OR parent_organization_unit_id <> organization_unit_id),
    CONSTRAINT organization_unit_version_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT organization_unit_version_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT organization_unit_bitemporal_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            organization_unit_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE TABLE job_profile (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    job_profile_id uuid PRIMARY KEY,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT job_profile_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT job_profile_tenant_identity_unique
        UNIQUE (tenant_record_id, job_profile_id)
);

CREATE TABLE job_profile_version (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    job_profile_version_id uuid PRIMARY KEY,
    job_profile_id uuid NOT NULL,
    job_title text NOT NULL,
    job_family_code text NOT NULL,
    job_version_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT job_profile_version_profile_tenant_fk
        FOREIGN KEY (tenant_record_id, job_profile_id)
        REFERENCES job_profile(tenant_record_id, job_profile_id),
    CONSTRAINT job_profile_version_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT job_profile_version_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT job_profile_bitemporal_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            job_profile_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE TABLE position_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    position_record_id uuid PRIMARY KEY,
    organization_unit_id uuid NOT NULL,
    job_profile_id uuid NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT position_organization_tenant_fk
        FOREIGN KEY (tenant_record_id, organization_unit_id)
        REFERENCES organization_unit(tenant_record_id, organization_unit_id),
    CONSTRAINT position_job_profile_tenant_fk
        FOREIGN KEY (tenant_record_id, job_profile_id)
        REFERENCES job_profile(tenant_record_id, job_profile_id),
    CONSTRAINT position_record_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT position_record_tenant_identity_unique
        UNIQUE (tenant_record_id, position_record_id)
);

CREATE TABLE position_record_version (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    position_record_version_id uuid PRIMARY KEY,
    position_record_id uuid NOT NULL,
    position_status_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT position_version_record_tenant_fk
        FOREIGN KEY (tenant_record_id, position_record_id)
        REFERENCES position_record(tenant_record_id, position_record_id),
    CONSTRAINT position_version_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT position_version_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT position_record_bitemporal_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            position_record_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE TABLE assignment_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    assignment_record_id uuid PRIMARY KEY,
    employment_record_id uuid NOT NULL,
    person_record_id uuid NOT NULL,
    position_record_id uuid NOT NULL,
    allocation_ratio numeric(5,4) NOT NULL
        CONSTRAINT assignment_allocation_ratio_check
        CHECK (allocation_ratio > 0 AND allocation_ratio <= 1),
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT assignment_employment_person_tenant_fk
        FOREIGN KEY (tenant_record_id, employment_record_id, person_record_id)
        REFERENCES employment_record(tenant_record_id, employment_record_id, person_record_id),
    CONSTRAINT assignment_position_tenant_fk
        FOREIGN KEY (tenant_record_id, position_record_id)
        REFERENCES position_record(tenant_record_id, position_record_id),
    CONSTRAINT assignment_record_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT assignment_record_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT assignment_record_tenant_identity_unique
        UNIQUE (tenant_record_id, assignment_record_id)
);

CREATE TABLE candidate_profile (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    candidate_profile_id uuid PRIMARY KEY,
    application_status_code text NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT candidate_profile_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT candidate_profile_tenant_identity_unique
        UNIQUE (tenant_record_id, candidate_profile_id)
);

CREATE TABLE candidate_worker_link (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    candidate_worker_link_id uuid PRIMARY KEY,
    candidate_profile_id uuid NOT NULL,
    person_record_id uuid NOT NULL,
    linked_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT candidate_worker_candidate_tenant_fk
        FOREIGN KEY (tenant_record_id, candidate_profile_id)
        REFERENCES candidate_profile(tenant_record_id, candidate_profile_id),
    CONSTRAINT candidate_worker_person_tenant_fk
        FOREIGN KEY (tenant_record_id, person_record_id)
        REFERENCES person_record(tenant_record_id, person_record_id),
    CONSTRAINT candidate_worker_tenant_candidate_unique
        UNIQUE (tenant_record_id, candidate_profile_id)
);

CREATE TABLE performance_cycle (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
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
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT performance_cycle_tenant_identity_unique
        UNIQUE (tenant_record_id, performance_cycle_id)
);

CREATE TABLE criterion_blueprint (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    criterion_blueprint_id uuid PRIMARY KEY,
    job_profile_id uuid NOT NULL,
    criterion_type_code text NOT NULL,
    criterion_version_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT criterion_blueprint_job_tenant_fk
        FOREIGN KEY (tenant_record_id, job_profile_id)
        REFERENCES job_profile(tenant_record_id, job_profile_id),
    CONSTRAINT criterion_blueprint_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT criterion_blueprint_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT criterion_blueprint_tenant_identity_unique
        UNIQUE (tenant_record_id, criterion_blueprint_id)
);

CREATE TABLE criterion_observation (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    criterion_observation_id uuid PRIMARY KEY,
    criterion_blueprint_id uuid NOT NULL,
    performance_cycle_id uuid NOT NULL,
    person_record_id uuid NOT NULL,
    observed_value numeric NOT NULL,
    observed_at timestamptz NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT criterion_observation_blueprint_tenant_fk
        FOREIGN KEY (tenant_record_id, criterion_blueprint_id)
        REFERENCES criterion_blueprint(tenant_record_id, criterion_blueprint_id),
    CONSTRAINT criterion_observation_cycle_tenant_fk
        FOREIGN KEY (tenant_record_id, performance_cycle_id)
        REFERENCES performance_cycle(tenant_record_id, performance_cycle_id),
    CONSTRAINT criterion_observation_person_tenant_fk
        FOREIGN KEY (tenant_record_id, person_record_id)
        REFERENCES person_record(tenant_record_id, person_record_id),
    CONSTRAINT criterion_observation_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT criterion_observation_tenant_identity_unique
        UNIQUE (tenant_record_id, criterion_observation_id)
);

CREATE TABLE decision_evidence_set (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    decision_evidence_set_id uuid PRIMARY KEY,
    evidence_set_version_code text NOT NULL,
    digest_algorithm_code text NOT NULL,
    evidence_set_digest text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    sealed_at timestamptz,
    sealed_selection_decision_id uuid,
    CONSTRAINT decision_evidence_digest_algorithm_check
        CHECK (digest_algorithm_code = 'sha256'),
    CONSTRAINT decision_evidence_digest_format_check
        CHECK (evidence_set_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT decision_evidence_seal_pair_check
        CHECK ((sealed_at IS NULL) = (sealed_selection_decision_id IS NULL)),
    CONSTRAINT decision_evidence_set_tenant_identity_unique
        UNIQUE (tenant_record_id, decision_evidence_set_id)
);

CREATE TABLE selection_decision_evidence (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    selection_decision_evidence_id uuid PRIMARY KEY,
    decision_evidence_set_id uuid NOT NULL,
    evidence_reference text NOT NULL,
    evidence_version_code text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT selection_evidence_set_tenant_fk
        FOREIGN KEY (tenant_record_id, decision_evidence_set_id)
        REFERENCES decision_evidence_set(tenant_record_id, decision_evidence_set_id),
    CONSTRAINT selection_decision_evidence_unique
        UNIQUE (tenant_record_id, decision_evidence_set_id, evidence_reference, evidence_version_code)
);

CREATE TABLE selection_decision (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    selection_decision_id uuid PRIMARY KEY,
    candidate_profile_id uuid NOT NULL,
    job_profile_id uuid NOT NULL,
    decision_evidence_set_id uuid NOT NULL,
    actor_reference text NOT NULL,
    purpose_code text NOT NULL,
    decision_code text NOT NULL,
    decision_reason text NOT NULL,
    confirmation_reference text NOT NULL,
    decided_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT selection_decision_candidate_tenant_fk
        FOREIGN KEY (tenant_record_id, candidate_profile_id)
        REFERENCES candidate_profile(tenant_record_id, candidate_profile_id),
    CONSTRAINT selection_decision_job_tenant_fk
        FOREIGN KEY (tenant_record_id, job_profile_id)
        REFERENCES job_profile(tenant_record_id, job_profile_id),
    CONSTRAINT selection_decision_evidence_set_tenant_fk
        FOREIGN KEY (tenant_record_id, decision_evidence_set_id)
        REFERENCES decision_evidence_set(tenant_record_id, decision_evidence_set_id),
    CONSTRAINT selection_decision_evidence_set_unique
        UNIQUE (tenant_record_id, decision_evidence_set_id),
    CONSTRAINT selection_decision_tenant_identity_unique
        UNIQUE (tenant_record_id, selection_decision_id)
);

ALTER TABLE decision_evidence_set
ADD CONSTRAINT decision_evidence_sealed_decision_tenant_fk
FOREIGN KEY (tenant_record_id, sealed_selection_decision_id)
REFERENCES selection_decision(tenant_record_id, selection_decision_id)
DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE validity_study (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    validity_study_id uuid PRIMARY KEY,
    criterion_blueprint_id uuid NOT NULL,
    study_status_code text NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT validity_study_blueprint_tenant_fk
        FOREIGN KEY (tenant_record_id, criterion_blueprint_id)
        REFERENCES criterion_blueprint(tenant_record_id, criterion_blueprint_id),
    CONSTRAINT validity_study_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT validity_study_tenant_identity_unique
        UNIQUE (tenant_record_id, validity_study_id)
);

CREATE TABLE validity_study_decision_link (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    validity_study_decision_link_id uuid PRIMARY KEY,
    validity_study_id uuid NOT NULL,
    selection_decision_id uuid NOT NULL,
    linked_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT validity_decision_study_tenant_fk
        FOREIGN KEY (tenant_record_id, validity_study_id)
        REFERENCES validity_study(tenant_record_id, validity_study_id),
    CONSTRAINT validity_decision_selection_tenant_fk
        FOREIGN KEY (tenant_record_id, selection_decision_id)
        REFERENCES selection_decision(tenant_record_id, selection_decision_id),
    CONSTRAINT validity_study_decision_unique
        UNIQUE (tenant_record_id, validity_study_id, selection_decision_id)
);

CREATE TABLE validity_study_outcome_link (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    validity_study_outcome_link_id uuid PRIMARY KEY,
    validity_study_id uuid NOT NULL,
    criterion_observation_id uuid NOT NULL,
    linked_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT validity_outcome_study_tenant_fk
        FOREIGN KEY (tenant_record_id, validity_study_id)
        REFERENCES validity_study(tenant_record_id, validity_study_id),
    CONSTRAINT validity_outcome_observation_tenant_fk
        FOREIGN KEY (tenant_record_id, criterion_observation_id)
        REFERENCES criterion_observation(tenant_record_id, criterion_observation_id),
    CONSTRAINT validity_study_outcome_unique
        UNIQUE (tenant_record_id, validity_study_id, criterion_observation_id)
);

CREATE TABLE validity_study_evidence_set_link (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    validity_study_evidence_set_link_id uuid PRIMARY KEY,
    validity_study_id uuid NOT NULL,
    decision_evidence_set_id uuid NOT NULL,
    linked_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT validity_evidence_study_tenant_fk
        FOREIGN KEY (tenant_record_id, validity_study_id)
        REFERENCES validity_study(tenant_record_id, validity_study_id),
    CONSTRAINT validity_evidence_set_tenant_fk
        FOREIGN KEY (tenant_record_id, decision_evidence_set_id)
        REFERENCES decision_evidence_set(tenant_record_id, decision_evidence_set_id),
    CONSTRAINT validity_study_evidence_set_unique
        UNIQUE (tenant_record_id, validity_study_id, decision_evidence_set_id)
);

CREATE TABLE compensation_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    compensation_record_id uuid PRIMARY KEY,
    person_record_id uuid NOT NULL,
    amount_value numeric NOT NULL,
    currency_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT compensation_person_tenant_fk
        FOREIGN KEY (tenant_record_id, person_record_id)
        REFERENCES person_record(tenant_record_id, person_record_id),
    CONSTRAINT compensation_record_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT compensation_record_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from)
);

CREATE TABLE employment_transition (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    employment_transition_id uuid PRIMARY KEY,
    employment_record_id uuid NOT NULL,
    transition_type_code text NOT NULL,
    effective_date date NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT employment_transition_record_tenant_fk
        FOREIGN KEY (tenant_record_id, employment_record_id)
        REFERENCES employment_record(tenant_record_id, employment_record_id),
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

CREATE TRIGGER person_record_bitemporal_guard
BEFORE UPDATE OR DELETE ON person_record
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER person_name_bitemporal_guard
BEFORE UPDATE OR DELETE ON person_name_record
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER employment_record_bitemporal_guard
BEFORE UPDATE OR DELETE ON employment_record
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER employment_record_version_bitemporal_guard
BEFORE UPDATE OR DELETE ON employment_record_version
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER organization_unit_anchor_bitemporal_guard
BEFORE UPDATE OR DELETE ON organization_unit
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER organization_unit_bitemporal_guard
BEFORE UPDATE OR DELETE ON organization_unit_version
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER job_profile_anchor_bitemporal_guard
BEFORE UPDATE OR DELETE ON job_profile
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER job_profile_bitemporal_guard
BEFORE UPDATE OR DELETE ON job_profile_version
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER position_record_bitemporal_guard
BEFORE UPDATE OR DELETE ON position_record
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER position_record_version_bitemporal_guard
BEFORE UPDATE OR DELETE ON position_record_version
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER assignment_record_bitemporal_guard
BEFORE UPDATE OR DELETE ON assignment_record
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER candidate_profile_bitemporal_guard
BEFORE UPDATE OR DELETE ON candidate_profile
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER performance_cycle_bitemporal_guard
BEFORE UPDATE OR DELETE ON performance_cycle
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER criterion_blueprint_bitemporal_guard
BEFORE UPDATE OR DELETE ON criterion_blueprint
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER criterion_observation_bitemporal_guard
BEFORE UPDATE OR DELETE ON criterion_observation
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER validity_study_bitemporal_guard
BEFORE UPDATE OR DELETE ON validity_study
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER compensation_record_bitemporal_guard
BEFORE UPDATE OR DELETE ON compensation_record
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER employment_transition_bitemporal_guard
BEFORE UPDATE OR DELETE ON employment_transition
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

CREATE FUNCTION protect_evidence_set_seal()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'decision evidence set cannot be deleted'
            USING ERRCODE = '55000';
    END IF;

    IF OLD.sealed_at IS NOT NULL
       OR OLD.sealed_selection_decision_id IS NOT NULL
       OR NEW.sealed_at IS NULL
       OR NEW.sealed_selection_decision_id IS NULL
       OR to_jsonb(NEW) - 'sealed_at' - 'sealed_selection_decision_id'
          <> to_jsonb(OLD) - 'sealed_at' - 'sealed_selection_decision_id' THEN
        RAISE EXCEPTION 'decision evidence set may only transition once from open to sealed'
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$$;

CREATE FUNCTION reject_sealed_evidence_insert()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    sealed_decision_id uuid;
BEGIN
    SELECT sealed_selection_decision_id
    INTO sealed_decision_id
    FROM decision_evidence_set
    WHERE tenant_record_id = NEW.tenant_record_id
      AND decision_evidence_set_id = NEW.decision_evidence_set_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'decision evidence set does not exist in the tenant'
            USING ERRCODE = '23503';
    END IF;

    IF sealed_decision_id IS NOT NULL THEN
        RAISE EXCEPTION 'sealed evidence set cannot accept new members'
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$$;

CREATE FUNCTION seal_decision_evidence_set()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE decision_evidence_set
    SET sealed_at = NEW.recorded_at,
        sealed_selection_decision_id = NEW.selection_decision_id
    WHERE tenant_record_id = NEW.tenant_record_id
      AND decision_evidence_set_id = NEW.decision_evidence_set_id
      AND sealed_selection_decision_id IS NULL;

    IF FOUND THEN
        RETURN NEW;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM decision_evidence_set
        WHERE tenant_record_id = NEW.tenant_record_id
          AND decision_evidence_set_id = NEW.decision_evidence_set_id
    ) THEN
        RAISE EXCEPTION 'evidence set is already sealed by a decision'
            USING ERRCODE = '55000';
    END IF;

    RAISE EXCEPTION 'decision evidence set does not exist in the tenant'
        USING ERRCODE = '23503';
END;
$$;

CREATE TRIGGER candidate_worker_link_append_only_guard
BEFORE UPDATE OR DELETE ON candidate_worker_link
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER decision_evidence_set_seal_guard
BEFORE UPDATE OR DELETE ON decision_evidence_set
FOR EACH ROW
EXECUTE FUNCTION protect_evidence_set_seal();

CREATE TRIGGER selection_evidence_insert_guard
BEFORE INSERT ON selection_decision_evidence
FOR EACH ROW
EXECUTE FUNCTION reject_sealed_evidence_insert();

CREATE TRIGGER selection_decision_seal_evidence_guard
BEFORE INSERT ON selection_decision
FOR EACH ROW
EXECUTE FUNCTION seal_decision_evidence_set();

CREATE TRIGGER selection_decision_append_only_guard
BEFORE UPDATE OR DELETE ON selection_decision
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER selection_decision_evidence_append_only_guard
BEFORE UPDATE OR DELETE ON selection_decision_evidence
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER validity_study_decision_append_only_guard
BEFORE UPDATE OR DELETE ON validity_study_decision_link
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER validity_study_outcome_append_only_guard
BEFORE UPDATE OR DELETE ON validity_study_outcome_link
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER validity_study_evidence_append_only_guard
BEFORE UPDATE OR DELETE ON validity_study_evidence_set_link
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE FUNCTION current_tenant_record_id()
RETURNS uuid
LANGUAGE sql
STABLE
PARALLEL SAFE
AS $$
    SELECT NULLIF(current_setting('orgmetra.tenant_record_id', true), '')::uuid
$$;

ALTER TABLE tenant_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_record FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_record_scope_policy ON tenant_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE person_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE person_record FORCE ROW LEVEL SECURITY;
CREATE POLICY person_record_scope_policy ON person_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE person_name_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE person_name_record FORCE ROW LEVEL SECURITY;
CREATE POLICY person_name_scope_policy ON person_name_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE employment_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE employment_record FORCE ROW LEVEL SECURITY;
CREATE POLICY employment_record_scope_policy ON employment_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE employment_record_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE employment_record_version FORCE ROW LEVEL SECURITY;
CREATE POLICY employment_version_scope_policy ON employment_record_version
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE organization_unit ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_unit FORCE ROW LEVEL SECURITY;
CREATE POLICY organization_unit_scope_policy ON organization_unit
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE organization_unit_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_unit_version FORCE ROW LEVEL SECURITY;
CREATE POLICY organization_version_scope_policy ON organization_unit_version
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE job_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_profile FORCE ROW LEVEL SECURITY;
CREATE POLICY job_profile_scope_policy ON job_profile
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE job_profile_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_profile_version FORCE ROW LEVEL SECURITY;
CREATE POLICY job_profile_version_scope_policy ON job_profile_version
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE position_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE position_record FORCE ROW LEVEL SECURITY;
CREATE POLICY position_record_scope_policy ON position_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE position_record_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE position_record_version FORCE ROW LEVEL SECURITY;
CREATE POLICY position_version_scope_policy ON position_record_version
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE assignment_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE assignment_record FORCE ROW LEVEL SECURITY;
CREATE POLICY assignment_record_scope_policy ON assignment_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE candidate_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_profile FORCE ROW LEVEL SECURITY;
CREATE POLICY candidate_profile_scope_policy ON candidate_profile
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE candidate_worker_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_worker_link FORCE ROW LEVEL SECURITY;
CREATE POLICY candidate_worker_scope_policy ON candidate_worker_link
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE performance_cycle ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_cycle FORCE ROW LEVEL SECURITY;
CREATE POLICY performance_cycle_scope_policy ON performance_cycle
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE criterion_blueprint ENABLE ROW LEVEL SECURITY;
ALTER TABLE criterion_blueprint FORCE ROW LEVEL SECURITY;
CREATE POLICY criterion_blueprint_scope_policy ON criterion_blueprint
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE criterion_observation ENABLE ROW LEVEL SECURITY;
ALTER TABLE criterion_observation FORCE ROW LEVEL SECURITY;
CREATE POLICY criterion_observation_scope_policy ON criterion_observation
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE decision_evidence_set ENABLE ROW LEVEL SECURITY;
ALTER TABLE decision_evidence_set FORCE ROW LEVEL SECURITY;
CREATE POLICY decision_evidence_scope_policy ON decision_evidence_set
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE selection_decision_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE selection_decision_evidence FORCE ROW LEVEL SECURITY;
CREATE POLICY selection_evidence_scope_policy ON selection_decision_evidence
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE selection_decision ENABLE ROW LEVEL SECURITY;
ALTER TABLE selection_decision FORCE ROW LEVEL SECURITY;
CREATE POLICY selection_decision_scope_policy ON selection_decision
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE validity_study ENABLE ROW LEVEL SECURITY;
ALTER TABLE validity_study FORCE ROW LEVEL SECURITY;
CREATE POLICY validity_study_scope_policy ON validity_study
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE validity_study_decision_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE validity_study_decision_link FORCE ROW LEVEL SECURITY;
CREATE POLICY validity_decision_scope_policy ON validity_study_decision_link
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE validity_study_outcome_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE validity_study_outcome_link FORCE ROW LEVEL SECURITY;
CREATE POLICY validity_outcome_scope_policy ON validity_study_outcome_link
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE validity_study_evidence_set_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE validity_study_evidence_set_link FORCE ROW LEVEL SECURITY;
CREATE POLICY validity_evidence_scope_policy ON validity_study_evidence_set_link
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE compensation_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE compensation_record FORCE ROW LEVEL SECURITY;
CREATE POLICY compensation_record_scope_policy ON compensation_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE employment_transition ENABLE ROW LEVEL SECURITY;
ALTER TABLE employment_transition FORCE ROW LEVEL SECURITY;
CREATE POLICY employment_transition_scope_policy ON employment_transition
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());
