-- Persist one immutable job-analysis snapshot in 3NF.
-- The kernel JobAnalysisSnapshot remains the in-process evidence contract.
-- This migration stores that contract as tenant-scoped rows bound to the
-- existing job, and optionally position and criterion, identities.
-- A missing parent identity fails closed through tenant-qualified foreign keys.

CREATE TABLE job_analysis_snapshot (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    analysis_record_id uuid PRIMARY KEY,
    job_profile_id uuid NOT NULL,
    position_record_id uuid,
    criterion_blueprint_id uuid,
    analysis_version_code text NOT NULL,
    status_code text NOT NULL,
    effective_from date NOT NULL,
    recorded_at timestamptz NOT NULL,
    reviewed_by_reference text,
    reviewed_at timestamptz,
    content_digest_sha256 text NOT NULL,
    data_function_code integer NOT NULL,
    people_function_code integer NOT NULL,
    things_function_code integer NOT NULL,
    fja_source_uri text NOT NULL,
    fja_source_title text NOT NULL,
    fja_source_version_code text NOT NULL,
    fja_retrieved_at timestamptz NOT NULL,
    fja_content_digest_sha256 text NOT NULL,
    fja_origin_code text NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT job_analysis_snapshot_job_tenant_fk
        FOREIGN KEY (tenant_record_id, job_profile_id)
        REFERENCES job_profile(tenant_record_id, job_profile_id),
    CONSTRAINT job_analysis_snapshot_position_tenant_fk
        FOREIGN KEY (tenant_record_id, position_record_id)
        REFERENCES position_record(tenant_record_id, position_record_id),
    CONSTRAINT job_analysis_snapshot_criterion_tenant_fk
        FOREIGN KEY (tenant_record_id, criterion_blueprint_id)
        REFERENCES criterion_blueprint(tenant_record_id, criterion_blueprint_id),
    CONSTRAINT job_analysis_snapshot_tenant_identity_unique
        UNIQUE (tenant_record_id, analysis_record_id),
    CONSTRAINT job_analysis_snapshot_job_version_unique
        UNIQUE (tenant_record_id, job_profile_id, analysis_version_code),
    CONSTRAINT job_analysis_snapshot_status_code_check
        CHECK (status_code IN ('analysis_draft', 'analysis_validated')),
    CONSTRAINT job_analysis_snapshot_digest_format_check
        CHECK (content_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_analysis_snapshot_fja_digest_format_check
        CHECK (fja_content_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_analysis_snapshot_data_function_check
        CHECK (data_function_code BETWEEN 0 AND 6),
    CONSTRAINT job_analysis_snapshot_people_function_check
        CHECK (people_function_code BETWEEN 0 AND 8),
    CONSTRAINT job_analysis_snapshot_things_function_check
        CHECK (things_function_code BETWEEN 0 AND 7),
    CONSTRAINT job_analysis_snapshot_review_pair_check
        CHECK ((reviewed_by_reference IS NULL) = (reviewed_at IS NULL)),
    CONSTRAINT job_analysis_snapshot_tenant_operational_uuid_check
        CHECK (is_operational_uuid(tenant_record_id)),
    CONSTRAINT job_analysis_snapshot_analysis_operational_uuid_check
        CHECK (is_operational_uuid(analysis_record_id)),
    CONSTRAINT job_analysis_snapshot_job_operational_uuid_check
        CHECK (is_operational_uuid(job_profile_id)),
    CONSTRAINT job_analysis_snapshot_position_operational_uuid_check
        CHECK (position_record_id IS NULL OR is_operational_uuid(position_record_id)),
    CONSTRAINT job_analysis_snapshot_criterion_operational_uuid_check
        CHECK (criterion_blueprint_id IS NULL OR is_operational_uuid(criterion_blueprint_id))
);

CREATE TABLE job_analysis_task_item (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    analysis_record_id uuid NOT NULL,
    task_record_id uuid NOT NULL,
    task_statement text NOT NULL,
    importance_level integer NOT NULL,
    difficulty_level integer NOT NULL,
    source_uri text NOT NULL,
    source_title text NOT NULL,
    source_version_code text NOT NULL,
    retrieved_at timestamptz NOT NULL,
    content_digest_sha256 text NOT NULL,
    origin_code text NOT NULL,
    CONSTRAINT job_analysis_task_item_pk
        PRIMARY KEY (tenant_record_id, analysis_record_id, task_record_id),
    CONSTRAINT job_analysis_task_snapshot_tenant_fk
        FOREIGN KEY (tenant_record_id, analysis_record_id)
        REFERENCES job_analysis_snapshot(tenant_record_id, analysis_record_id),
    CONSTRAINT job_analysis_task_item_identity_unique
        UNIQUE (tenant_record_id, task_record_id, analysis_record_id),
    CONSTRAINT job_analysis_task_importance_level_check
        CHECK (importance_level BETWEEN 1 AND 5),
    CONSTRAINT job_analysis_task_difficulty_level_check
        CHECK (difficulty_level BETWEEN 1 AND 5),
    CONSTRAINT job_analysis_task_digest_format_check
        CHECK (content_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_analysis_task_tenant_operational_uuid_check
        CHECK (is_operational_uuid(tenant_record_id)),
    CONSTRAINT job_analysis_task_analysis_operational_uuid_check
        CHECK (is_operational_uuid(analysis_record_id)),
    CONSTRAINT job_analysis_task_record_operational_uuid_check
        CHECK (is_operational_uuid(task_record_id))
);

CREATE TABLE job_analysis_ksao_item (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    analysis_record_id uuid NOT NULL,
    ksao_record_id uuid NOT NULL,
    category_code text NOT NULL,
    requirement_statement text NOT NULL,
    importance_level integer NOT NULL,
    proficiency_level integer NOT NULL,
    source_uri text NOT NULL,
    source_title text NOT NULL,
    source_version_code text NOT NULL,
    retrieved_at timestamptz NOT NULL,
    content_digest_sha256 text NOT NULL,
    origin_code text NOT NULL,
    CONSTRAINT job_analysis_ksao_item_pk
        PRIMARY KEY (tenant_record_id, analysis_record_id, ksao_record_id),
    CONSTRAINT job_analysis_ksao_snapshot_tenant_fk
        FOREIGN KEY (tenant_record_id, analysis_record_id)
        REFERENCES job_analysis_snapshot(tenant_record_id, analysis_record_id),
    CONSTRAINT job_analysis_ksao_item_identity_unique
        UNIQUE (tenant_record_id, ksao_record_id, analysis_record_id),
    CONSTRAINT job_analysis_ksao_category_code_check
        CHECK (category_code IN (
            'knowledge_requirement',
            'skill_requirement',
            'ability_requirement',
            'other_characteristic'
        )),
    CONSTRAINT job_analysis_ksao_importance_level_check
        CHECK (importance_level BETWEEN 1 AND 5),
    CONSTRAINT job_analysis_ksao_proficiency_level_check
        CHECK (proficiency_level BETWEEN 1 AND 5),
    CONSTRAINT job_analysis_ksao_digest_format_check
        CHECK (content_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_analysis_ksao_tenant_operational_uuid_check
        CHECK (is_operational_uuid(tenant_record_id)),
    CONSTRAINT job_analysis_ksao_analysis_operational_uuid_check
        CHECK (is_operational_uuid(analysis_record_id)),
    CONSTRAINT job_analysis_ksao_record_operational_uuid_check
        CHECK (is_operational_uuid(ksao_record_id))
);

CREATE TABLE job_analysis_task_ksao_link (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    analysis_record_id uuid NOT NULL,
    task_record_id uuid NOT NULL,
    ksao_record_id uuid NOT NULL,
    relationship_strength integer NOT NULL,
    essential_for_task boolean NOT NULL,
    CONSTRAINT job_analysis_task_ksao_link_pk
        PRIMARY KEY (tenant_record_id, analysis_record_id, task_record_id, ksao_record_id),
    CONSTRAINT job_analysis_link_task_tenant_fk
        FOREIGN KEY (tenant_record_id, analysis_record_id, task_record_id)
        REFERENCES job_analysis_task_item(tenant_record_id, analysis_record_id, task_record_id),
    CONSTRAINT job_analysis_link_ksao_tenant_fk
        FOREIGN KEY (tenant_record_id, analysis_record_id, ksao_record_id)
        REFERENCES job_analysis_ksao_item(tenant_record_id, analysis_record_id, ksao_record_id),
    CONSTRAINT job_analysis_link_strength_check
        CHECK (relationship_strength BETWEEN 1 AND 5),
    CONSTRAINT job_analysis_link_tenant_operational_uuid_check
        CHECK (is_operational_uuid(tenant_record_id)),
    CONSTRAINT job_analysis_link_analysis_operational_uuid_check
        CHECK (is_operational_uuid(analysis_record_id)),
    CONSTRAINT job_analysis_link_task_operational_uuid_check
        CHECK (is_operational_uuid(task_record_id)),
    CONSTRAINT job_analysis_link_ksao_operational_uuid_check
        CHECK (is_operational_uuid(ksao_record_id))
);

CREATE TABLE job_analysis_write_command (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    write_command_id uuid PRIMARY KEY,
    analysis_record_id uuid NOT NULL,
    idempotency_key text NOT NULL,
    request_digest_sha256 text NOT NULL,
    actor_reference text NOT NULL,
    purpose_code text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT job_analysis_write_command_snapshot_tenant_fk
        FOREIGN KEY (tenant_record_id, analysis_record_id)
        REFERENCES job_analysis_snapshot(tenant_record_id, analysis_record_id),
    CONSTRAINT job_analysis_write_command_tenant_identity_unique
        UNIQUE (tenant_record_id, write_command_id),
    CONSTRAINT job_analysis_write_command_idempotency_unique
        UNIQUE (tenant_record_id, idempotency_key),
    CONSTRAINT job_analysis_write_command_digest_format_check
        CHECK (request_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_analysis_write_command_key_length_check
        CHECK (char_length(idempotency_key) BETWEEN 16 AND 200),
    CONSTRAINT job_analysis_write_command_tenant_operational_uuid_check
        CHECK (is_operational_uuid(tenant_record_id)),
    CONSTRAINT job_analysis_write_command_id_operational_uuid_check
        CHECK (is_operational_uuid(write_command_id)),
    CONSTRAINT job_analysis_write_command_analysis_operational_uuid_check
        CHECK (is_operational_uuid(analysis_record_id))
);

CREATE TRIGGER job_analysis_snapshot_append_only_guard
BEFORE UPDATE OR DELETE ON job_analysis_snapshot
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER job_analysis_task_item_append_only_guard
BEFORE UPDATE OR DELETE ON job_analysis_task_item
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER job_analysis_ksao_item_append_only_guard
BEFORE UPDATE OR DELETE ON job_analysis_ksao_item
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER job_analysis_task_ksao_link_append_only_guard
BEFORE UPDATE OR DELETE ON job_analysis_task_ksao_link
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER job_analysis_write_command_append_only_guard
BEFORE UPDATE OR DELETE ON job_analysis_write_command
FOR EACH ROW
EXECUTE FUNCTION reject_append_only_mutation();

ALTER TABLE job_analysis_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_analysis_snapshot FORCE ROW LEVEL SECURITY;
CREATE POLICY job_analysis_snapshot_scope_policy ON job_analysis_snapshot
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE job_analysis_task_item ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_analysis_task_item FORCE ROW LEVEL SECURITY;
CREATE POLICY job_analysis_task_item_scope_policy ON job_analysis_task_item
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE job_analysis_ksao_item ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_analysis_ksao_item FORCE ROW LEVEL SECURITY;
CREATE POLICY job_analysis_ksao_item_scope_policy ON job_analysis_ksao_item
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE job_analysis_task_ksao_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_analysis_task_ksao_link FORCE ROW LEVEL SECURITY;
CREATE POLICY job_analysis_task_ksao_link_scope_policy ON job_analysis_task_ksao_link
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE job_analysis_write_command ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_analysis_write_command FORCE ROW LEVEL SECURITY;
CREATE POLICY job_analysis_write_command_scope_policy ON job_analysis_write_command
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());
