BEGIN;

CREATE TABLE tenant_record (
    tenant_record_id uuid PRIMARY KEY,
    tenant_name text NOT NULL CHECK (length(btrim(tenant_name)) BETWEEN 1 AND 200),
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE person_record ADD COLUMN tenant_record_id uuid;
ALTER TABLE employment_record ADD COLUMN tenant_record_id uuid;
ALTER TABLE organization_unit ADD COLUMN tenant_record_id uuid;
ALTER TABLE job_profile ADD COLUMN tenant_record_id uuid;
ALTER TABLE position_record ADD COLUMN tenant_record_id uuid;
ALTER TABLE assignment_record ADD COLUMN tenant_record_id uuid;
ALTER TABLE candidate_profile ADD COLUMN tenant_record_id uuid;
ALTER TABLE candidate_worker_link ADD COLUMN tenant_record_id uuid;
ALTER TABLE criterion_blueprint ADD COLUMN tenant_record_id uuid;
ALTER TABLE criterion_observation ADD COLUMN tenant_record_id uuid;
ALTER TABLE selection_decision ADD COLUMN tenant_record_id uuid;
ALTER TABLE validity_study ADD COLUMN tenant_record_id uuid;
ALTER TABLE compensation_record ADD COLUMN tenant_record_id uuid;
ALTER TABLE employment_transition ADD COLUMN tenant_record_id uuid;

ALTER TABLE person_record
    ADD CONSTRAINT person_tenant_foreign_key
    FOREIGN KEY (tenant_record_id) REFERENCES tenant_record (tenant_record_id),
    ALTER COLUMN tenant_record_id SET NOT NULL,
    ADD CONSTRAINT person_tenant_identity_key
    UNIQUE (tenant_record_id, person_record_id);
ALTER TABLE employment_record
    ADD CONSTRAINT employment_tenant_foreign_key
    FOREIGN KEY (tenant_record_id) REFERENCES tenant_record (tenant_record_id),
    ALTER COLUMN tenant_record_id SET NOT NULL,
    ADD CONSTRAINT employment_tenant_identity_key
    UNIQUE (tenant_record_id, employment_record_id),
    ADD CONSTRAINT employment_person_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, person_record_id)
    REFERENCES person_record (tenant_record_id, person_record_id);
ALTER TABLE organization_unit
    ADD CONSTRAINT organization_tenant_foreign_key
    FOREIGN KEY (tenant_record_id) REFERENCES tenant_record (tenant_record_id),
    ALTER COLUMN tenant_record_id SET NOT NULL,
    ADD CONSTRAINT organization_tenant_identity_key
    UNIQUE (tenant_record_id, organization_unit_id);
ALTER TABLE job_profile
    ADD CONSTRAINT job_tenant_foreign_key
    FOREIGN KEY (tenant_record_id) REFERENCES tenant_record (tenant_record_id),
    ALTER COLUMN tenant_record_id SET NOT NULL,
    ADD CONSTRAINT job_tenant_identity_key
    UNIQUE (tenant_record_id, job_profile_id);
ALTER TABLE position_record
    ADD CONSTRAINT position_tenant_foreign_key
    FOREIGN KEY (tenant_record_id) REFERENCES tenant_record (tenant_record_id),
    ALTER COLUMN tenant_record_id SET NOT NULL,
    ADD CONSTRAINT position_tenant_identity_key
    UNIQUE (tenant_record_id, position_record_id),
    ADD CONSTRAINT position_organization_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, organization_unit_id)
    REFERENCES organization_unit (tenant_record_id, organization_unit_id),
    ADD CONSTRAINT position_job_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, job_profile_id)
    REFERENCES job_profile (tenant_record_id, job_profile_id);
ALTER TABLE assignment_record
    ADD CONSTRAINT assignment_tenant_foreign_key
    FOREIGN KEY (tenant_record_id) REFERENCES tenant_record (tenant_record_id),
    ALTER COLUMN tenant_record_id SET NOT NULL,
    ADD CONSTRAINT assignment_tenant_identity_key
    UNIQUE (tenant_record_id, assignment_record_id),
    ADD CONSTRAINT assignment_person_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, person_record_id)
    REFERENCES person_record (tenant_record_id, person_record_id),
    ADD CONSTRAINT assignment_position_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, position_record_id)
    REFERENCES position_record (tenant_record_id, position_record_id);
ALTER TABLE candidate_profile
    ADD CONSTRAINT candidate_tenant_foreign_key
    FOREIGN KEY (tenant_record_id) REFERENCES tenant_record (tenant_record_id),
    ALTER COLUMN tenant_record_id SET NOT NULL,
    ADD CONSTRAINT candidate_tenant_identity_key
    UNIQUE (tenant_record_id, candidate_profile_id);
ALTER TABLE candidate_worker_link
    ADD CONSTRAINT candidate_link_tenant_foreign_key
    FOREIGN KEY (tenant_record_id) REFERENCES tenant_record (tenant_record_id),
    ALTER COLUMN tenant_record_id SET NOT NULL,
    ADD CONSTRAINT candidate_link_tenant_identity_key
    UNIQUE (tenant_record_id, candidate_worker_link_id),
    ADD CONSTRAINT candidate_link_profile_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, candidate_profile_id)
    REFERENCES candidate_profile (tenant_record_id, candidate_profile_id),
    ADD CONSTRAINT candidate_link_person_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, person_record_id)
    REFERENCES person_record (tenant_record_id, person_record_id);
ALTER TABLE criterion_blueprint
    ADD CONSTRAINT criterion_tenant_foreign_key
    FOREIGN KEY (tenant_record_id) REFERENCES tenant_record (tenant_record_id),
    ALTER COLUMN tenant_record_id SET NOT NULL,
    ADD CONSTRAINT criterion_tenant_identity_key
    UNIQUE (tenant_record_id, criterion_blueprint_id),
    ADD CONSTRAINT criterion_job_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, job_profile_id)
    REFERENCES job_profile (tenant_record_id, job_profile_id);
ALTER TABLE criterion_observation
    ADD CONSTRAINT observation_tenant_foreign_key
    FOREIGN KEY (tenant_record_id) REFERENCES tenant_record (tenant_record_id),
    ALTER COLUMN tenant_record_id SET NOT NULL,
    ADD CONSTRAINT observation_tenant_identity_key
    UNIQUE (tenant_record_id, criterion_observation_id),
    ADD CONSTRAINT observation_criterion_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, criterion_blueprint_id)
    REFERENCES criterion_blueprint (tenant_record_id, criterion_blueprint_id),
    ADD CONSTRAINT observation_person_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, person_record_id)
    REFERENCES person_record (tenant_record_id, person_record_id);
ALTER TABLE selection_decision
    ADD CONSTRAINT selection_tenant_foreign_key
    FOREIGN KEY (tenant_record_id) REFERENCES tenant_record (tenant_record_id),
    ALTER COLUMN tenant_record_id SET NOT NULL,
    ADD CONSTRAINT selection_tenant_identity_key
    UNIQUE (tenant_record_id, selection_decision_id),
    ADD CONSTRAINT selection_candidate_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, candidate_profile_id)
    REFERENCES candidate_profile (tenant_record_id, candidate_profile_id),
    ADD CONSTRAINT selection_job_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, job_profile_id)
    REFERENCES job_profile (tenant_record_id, job_profile_id);
ALTER TABLE validity_study
    ADD CONSTRAINT validity_tenant_foreign_key
    FOREIGN KEY (tenant_record_id) REFERENCES tenant_record (tenant_record_id),
    ALTER COLUMN tenant_record_id SET NOT NULL,
    ADD CONSTRAINT validity_tenant_identity_key
    UNIQUE (tenant_record_id, validity_study_id),
    ADD CONSTRAINT validity_criterion_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, criterion_blueprint_id)
    REFERENCES criterion_blueprint (tenant_record_id, criterion_blueprint_id);
ALTER TABLE compensation_record
    ADD CONSTRAINT compensation_tenant_foreign_key
    FOREIGN KEY (tenant_record_id) REFERENCES tenant_record (tenant_record_id),
    ALTER COLUMN tenant_record_id SET NOT NULL,
    ADD CONSTRAINT compensation_tenant_identity_key
    UNIQUE (tenant_record_id, compensation_record_id),
    ADD CONSTRAINT compensation_person_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, person_record_id)
    REFERENCES person_record (tenant_record_id, person_record_id);
ALTER TABLE employment_transition
    ADD CONSTRAINT transition_tenant_foreign_key
    FOREIGN KEY (tenant_record_id) REFERENCES tenant_record (tenant_record_id),
    ALTER COLUMN tenant_record_id SET NOT NULL,
    ADD CONSTRAINT transition_tenant_identity_key
    UNIQUE (tenant_record_id, employment_transition_id),
    ADD CONSTRAINT transition_employment_tenant_foreign_key
    FOREIGN KEY (tenant_record_id, employment_record_id)
    REFERENCES employment_record (tenant_record_id, employment_record_id);

CREATE TABLE audit_event (
    audit_event_id uuid PRIMARY KEY,
    tenant_record_id uuid NOT NULL,
    actor_reference uuid NOT NULL,
    purpose_code text NOT NULL CHECK (length(btrim(purpose_code)) BETWEEN 1 AND 128),
    correlation_reference uuid NOT NULL,
    decision_reference uuid,
    evidence_reference text CHECK (
        evidence_reference IS NULL
        OR length(btrim(evidence_reference)) BETWEEN 1 AND 512
    ),
    action_code text NOT NULL CHECK (action_code ~ '^[a-z0-9_]+$'),
    resource_type_code text NOT NULL CHECK (resource_type_code ~ '^[a-z0-9_]+$'),
    resource_record_id uuid NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT audit_tenant_foreign_key
        FOREIGN KEY (tenant_record_id)
        REFERENCES tenant_record (tenant_record_id)
);
CREATE INDEX audit_resource_time_index
    ON audit_event (tenant_record_id, resource_record_id, occurred_at);
CREATE INDEX audit_correlation_time_index
    ON audit_event (tenant_record_id, correlation_reference, occurred_at);

CREATE FUNCTION current_tenant_reference()
RETURNS uuid
LANGUAGE sql
STABLE
SET search_path = pg_catalog, public
AS $$
    SELECT NULLIF(current_setting('orgmetra.tenant_reference', true), '')::uuid
$$;

DO $$
DECLARE
    protected_table text;
BEGIN
    FOREACH protected_table IN ARRAY ARRAY[
        'tenant_record',
        'person_record',
        'employment_record',
        'organization_unit',
        'job_profile',
        'position_record',
        'assignment_record',
        'candidate_profile',
        'candidate_worker_link',
        'criterion_blueprint',
        'criterion_observation',
        'selection_decision',
        'validity_study',
        'compensation_record',
        'employment_transition',
        'audit_event'
    ]
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', protected_table);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', protected_table);
        EXECUTE format(
            'CREATE POLICY %I ON %I USING (tenant_record_id = current_tenant_reference()) WITH CHECK (tenant_record_id = current_tenant_reference())',
            protected_table || '_tenant_policy',
            protected_table
        );
    END LOOP;
END
$$;

CREATE FUNCTION reject_immutable_fact_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    RAISE EXCEPTION 'immutable Orgmetra facts cannot be updated or deleted'
        USING ERRCODE = '55000';
END
$$;

CREATE TRIGGER audit_event_append_only_trigger
BEFORE UPDATE OR DELETE ON audit_event
FOR EACH ROW EXECUTE FUNCTION reject_immutable_fact_mutation();
CREATE TRIGGER candidate_link_append_only_trigger
BEFORE UPDATE OR DELETE ON candidate_worker_link
FOR EACH ROW EXECUTE FUNCTION reject_immutable_fact_mutation();
CREATE TRIGGER criterion_observation_append_only_trigger
BEFORE UPDATE OR DELETE ON criterion_observation
FOR EACH ROW EXECUTE FUNCTION reject_immutable_fact_mutation();
CREATE TRIGGER selection_decision_append_only_trigger
BEFORE UPDATE OR DELETE ON selection_decision
FOR EACH ROW EXECUTE FUNCTION reject_immutable_fact_mutation();
CREATE TRIGGER employment_transition_append_only_trigger
BEFORE UPDATE OR DELETE ON employment_transition
FOR EACH ROW EXECUTE FUNCTION reject_immutable_fact_mutation();

COMMIT;
