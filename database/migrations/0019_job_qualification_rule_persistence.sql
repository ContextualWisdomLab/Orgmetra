-- Persist human-reviewed Job qualification-rule evidence without granting
-- candidate or employment-decision authority. The reviewed artifact remains
-- value-minimized: raw rule text, candidate/person PII, cut scores, assessment
-- outcomes and model output are deliberately outside these relations.

SET search_path = public, pg_catalog;

CREATE TABLE job_qualification_rule_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    job_qualification_rule_record_id uuid PRIMARY KEY,
    job_profile_id uuid NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    recorded_to timestamptz,
    CONSTRAINT job_qualification_rule_record_id_operational_check
        CHECK (public.is_operational_uuid(job_qualification_rule_record_id)),
    CONSTRAINT job_qualification_rule_job_tenant_fk
        FOREIGN KEY (tenant_record_id, job_profile_id)
        REFERENCES job_profile(tenant_record_id, job_profile_id),
    CONSTRAINT job_qualification_rule_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT job_qualification_rule_record_tenant_identity_unique
        UNIQUE (tenant_record_id, job_qualification_rule_record_id)
);

CREATE TABLE job_qualification_rule_version (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    job_qualification_rule_version_id uuid PRIMARY KEY,
    job_qualification_rule_record_id uuid NOT NULL,
    analysis_record_id uuid NOT NULL,
    rule_category_code text NOT NULL,
    qualification_rule_artifact_digest_sha256 text NOT NULL,
    job_analysis_snapshot_digest_sha256 text NOT NULL,
    task_linkage_digest_sha256 text NOT NULL,
    ksao_linkage_digest_sha256 text NOT NULL,
    source_evidence_digest_sha256 text NOT NULL,
    review_evidence_digest_sha256 text NOT NULL,
    reviewer_actor_reference text NOT NULL,
    evidence_version integer NOT NULL,
    reviewed_at timestamptz NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    recorded_to timestamptz,
    audit_event_record_id uuid NOT NULL,
    activation_state text NOT NULL DEFAULT 'requires_authoritative_activation',
    decision_authority_state text NOT NULL
        DEFAULT 'not_authorized_for_candidate_or_employment_decision',
    CONSTRAINT job_qualification_rule_version_id_operational_check
        CHECK (public.is_operational_uuid(job_qualification_rule_version_id)),
    CONSTRAINT job_qualification_rule_version_record_tenant_fk
        FOREIGN KEY (tenant_record_id, job_qualification_rule_record_id)
        REFERENCES job_qualification_rule_record(
            tenant_record_id,
            job_qualification_rule_record_id
        ),
    CONSTRAINT job_qualification_rule_version_analysis_tenant_fk
        FOREIGN KEY (tenant_record_id, analysis_record_id)
        REFERENCES job_analysis_snapshot(tenant_record_id, analysis_record_id),
    CONSTRAINT job_qualification_rule_version_audit_tenant_fk
        FOREIGN KEY (tenant_record_id, audit_event_record_id)
        REFERENCES audit_event_record(tenant_record_id, audit_event_record_id),
    CONSTRAINT job_qualification_rule_category_check
        CHECK (rule_category_code IN (
            'credential_requirement',
            'education_training_requirement',
            'experience_requirement',
            'knowledge_skill_ability_requirement',
            'task_or_work_requirement'
        )),
    CONSTRAINT job_qualification_rule_artifact_digest_check
        CHECK (qualification_rule_artifact_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_qualification_rule_snapshot_digest_check
        CHECK (job_analysis_snapshot_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_qualification_rule_task_digest_check
        CHECK (task_linkage_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_qualification_rule_ksao_digest_check
        CHECK (ksao_linkage_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_qualification_rule_source_digest_check
        CHECK (source_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_qualification_rule_review_digest_check
        CHECK (review_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_qualification_rule_reviewer_actor_check
        CHECK (
            reviewer_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT job_qualification_rule_evidence_version_check
        CHECK (evidence_version BETWEEN 1 AND 2147483647),
    CONSTRAINT job_qualification_rule_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT job_qualification_rule_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT job_qualification_rule_review_chronology_check
        CHECK (reviewed_at <= recorded_from),
    CONSTRAINT job_qualification_rule_activation_state_check
        CHECK (activation_state = 'requires_authoritative_activation'),
    CONSTRAINT job_qualification_rule_decision_authority_check
        CHECK (
            decision_authority_state =
            'not_authorized_for_candidate_or_employment_decision'
        ),
    CONSTRAINT job_qualification_rule_version_tenant_identity_unique
        UNIQUE (tenant_record_id, job_qualification_rule_version_id),
    CONSTRAINT job_qualification_rule_audit_event_unique
        UNIQUE (tenant_record_id, audit_event_record_id),
    CONSTRAINT job_qualification_rule_bitemporal_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            job_qualification_rule_record_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE FUNCTION enforce_job_qualification_rule_system_time()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    IF NEW.recorded_to IS NOT NULL THEN
        RAISE EXCEPTION 'Job qualification-rule recorded_to must be NULL on insert'
            USING ERRCODE = '22023';
    END IF;
    IF NEW.recorded_from IS DISTINCT FROM pg_catalog.transaction_timestamp() THEN
        RAISE EXCEPTION 'Job qualification-rule recorded_from must equal the current transaction timestamp'
            USING ERRCODE = '22023';
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION enforce_job_qualification_rule_system_time() IS
    'Guards new Job qualification-rule anchors and versions: system-recorded time is PostgreSQL transaction time and new recorded intervals begin open.';

CREATE TRIGGER job_qualification_rule_record_system_time_guard
BEFORE INSERT ON job_qualification_rule_record
FOR EACH ROW
EXECUTE FUNCTION enforce_job_qualification_rule_system_time();

CREATE TRIGGER job_qualification_rule_version_system_time_guard
BEFORE INSERT ON job_qualification_rule_version
FOR EACH ROW
EXECUTE FUNCTION enforce_job_qualification_rule_system_time();

CREATE FUNCTION protect_job_qualification_rule_history()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Job qualification-rule history cannot be deleted'
            USING ERRCODE = '55000';
    END IF;

    IF OLD.recorded_to IS NOT NULL
       OR NEW.recorded_to IS NULL
       OR NEW.recorded_to IS DISTINCT FROM pg_catalog.transaction_timestamp()
       OR to_jsonb(NEW) - 'recorded_to' <> to_jsonb(OLD) - 'recorded_to' THEN
        RAISE EXCEPTION 'Job qualification-rule history may only close an open recorded interval at the current transaction timestamp'
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION protect_job_qualification_rule_history() IS
    'Preserves bitemporal Job qualification-rule evidence: DELETE and in-place rewrites fail closed; the only UPDATE is closing an open recorded interval at PostgreSQL transaction time.';

CREATE TRIGGER job_qualification_rule_record_history_guard
BEFORE UPDATE OR DELETE ON job_qualification_rule_record
FOR EACH ROW
EXECUTE FUNCTION protect_job_qualification_rule_history();

CREATE TRIGGER job_qualification_rule_version_history_guard
BEFORE UPDATE OR DELETE ON job_qualification_rule_version
FOR EACH ROW
EXECUTE FUNCTION protect_job_qualification_rule_history();

CREATE FUNCTION enforce_job_qualification_rule_scope()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    anchor_job_profile_id uuid;
    anchor_recorded_to timestamptz;
    snapshot_job_profile_id uuid;
    snapshot_status_code text;
    snapshot_digest text;
    snapshot_reviewed_by text;
    snapshot_reviewed_at timestamptz;
    audit_event jsonb;
    outbox_found boolean;
BEGIN
    SELECT job_profile_id, recorded_to
    INTO anchor_job_profile_id, anchor_recorded_to
    FROM job_qualification_rule_record
    WHERE tenant_record_id = NEW.tenant_record_id
      AND job_qualification_rule_record_id = NEW.job_qualification_rule_record_id
    FOR SHARE;

    IF NOT FOUND OR anchor_recorded_to IS NOT NULL THEN
        RAISE EXCEPTION 'Job qualification-rule version requires an open same-tenant rule anchor'
            USING ERRCODE = '23514';
    END IF;

    SELECT job_profile_id, status_code, content_digest_sha256,
           reviewed_by_reference, reviewed_at
    INTO snapshot_job_profile_id, snapshot_status_code, snapshot_digest,
         snapshot_reviewed_by, snapshot_reviewed_at
    FROM job_analysis_snapshot
    WHERE tenant_record_id = NEW.tenant_record_id
      AND analysis_record_id = NEW.analysis_record_id
    FOR SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Job qualification-rule version requires a same-tenant Job Analysis snapshot'
            USING ERRCODE = '23514';
    END IF;
    IF snapshot_job_profile_id IS DISTINCT FROM anchor_job_profile_id THEN
        RAISE EXCEPTION 'Job qualification-rule anchor and Job Analysis snapshot must resolve to the same Job'
            USING ERRCODE = '23514';
    END IF;
    IF snapshot_status_code <> 'analysis_validated'
       OR snapshot_reviewed_by IS NULL
       OR snapshot_reviewed_at IS NULL THEN
        RAISE EXCEPTION 'Job qualification-rule version requires a human-reviewed validated Job Analysis snapshot'
            USING ERRCODE = '23514';
    END IF;
    IF snapshot_digest IS DISTINCT FROM NEW.job_analysis_snapshot_digest_sha256 THEN
        RAISE EXCEPTION 'Job qualification-rule version snapshot digest does not match authoritative Job Analysis evidence'
            USING ERRCODE = '23514';
    END IF;

    SELECT canonical_event_json::jsonb
    INTO audit_event
    FROM audit_event_record
    WHERE tenant_record_id = NEW.tenant_record_id
      AND audit_event_record_id = NEW.audit_event_record_id
    FOR SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Job qualification-rule version requires immutable same-tenant audit evidence'
            USING ERRCODE = '23514';
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM outbox_delivery_record
        WHERE tenant_record_id = NEW.tenant_record_id
          AND audit_event_record_id = NEW.audit_event_record_id
          AND delivery_target_code = 'integration_hub'
    ) INTO outbox_found;

    IF NOT outbox_found THEN
        RAISE EXCEPTION 'Job qualification-rule version requires transactional audit/outbox evidence'
            USING ERRCODE = '23514';
    END IF;

    IF audit_event ->> 'orgmetrapurpose' <> 'job_qualification_rule_review'
       OR audit_event ->> 'orgmetraactor' <> NEW.reviewer_actor_reference
       OR audit_event ->> 'orgmetraevidence' <> NEW.review_evidence_digest_sha256
       OR audit_event ->> 'subject'
          <> 'job_qualification_rule:' || NEW.job_qualification_rule_record_id::text
       OR audit_event #>> '{data,result_code}' <> 'reviewed_for_authoritative_activation'
       OR (audit_event #>> '{data,high_impact}')::boolean IS DISTINCT FROM false
       OR (audit_event ->> 'time')::timestamptz IS DISTINCT FROM NEW.reviewed_at THEN
        RAISE EXCEPTION 'Job qualification-rule audit evidence does not exactly match the reviewed rule scope'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION enforce_job_qualification_rule_scope() IS
    'Before a rule version is persisted, re-resolves its open rule anchor, same Job validated Job Analysis snapshot, exact snapshot digest, human review provenance, immutable audit event and integration-hub outbox correlation. The persisted rule remains non-authorizing.';

CREATE TRIGGER job_qualification_rule_version_scope_guard
BEFORE INSERT ON job_qualification_rule_version
FOR EACH ROW
EXECUTE FUNCTION enforce_job_qualification_rule_scope();

CREATE FUNCTION enforce_job_qualification_rule_anchor_alignment()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    IF NEW.recorded_to IS NULL OR NEW.recorded_to IS NOT DISTINCT FROM OLD.recorded_to THEN
        RETURN NULL;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM job_qualification_rule_version AS version
        WHERE version.tenant_record_id = NEW.tenant_record_id
          AND version.job_qualification_rule_record_id = NEW.job_qualification_rule_record_id
          AND (version.recorded_to IS NULL OR version.recorded_to > NEW.recorded_to)
    ) THEN
        RAISE EXCEPTION 'cannot close Job qualification-rule anchor while a recorded version remains open'
            USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION enforce_job_qualification_rule_anchor_alignment() IS
    'Deferred anchor-closure guard: every version must be recorded closed no later than its durable rule anchor before commit.';

CREATE CONSTRAINT TRIGGER job_qualification_rule_anchor_alignment_guard
AFTER UPDATE ON job_qualification_rule_record
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION enforce_job_qualification_rule_anchor_alignment();

CREATE FUNCTION reject_job_qualification_rule_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'Job qualification-rule history cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION reject_job_qualification_rule_truncate() IS
    'Rejects table-wide TRUNCATE so governed Job qualification-rule evidence cannot bypass row-level bitemporal history guards.';

CREATE TRIGGER job_qualification_rule_record_truncate_guard
BEFORE TRUNCATE ON job_qualification_rule_record
FOR EACH STATEMENT
EXECUTE FUNCTION reject_job_qualification_rule_truncate();

CREATE TRIGGER job_qualification_rule_version_truncate_guard
BEFORE TRUNCATE ON job_qualification_rule_version
FOR EACH STATEMENT
EXECUTE FUNCTION reject_job_qualification_rule_truncate();

REVOKE TRUNCATE ON job_qualification_rule_record FROM PUBLIC;
REVOKE TRUNCATE ON job_qualification_rule_version FROM PUBLIC;

ALTER TABLE job_qualification_rule_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_qualification_rule_record FORCE ROW LEVEL SECURITY;
CREATE POLICY job_qualification_rule_record_scope_policy
ON job_qualification_rule_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE job_qualification_rule_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_qualification_rule_version FORCE ROW LEVEL SECURITY;
CREATE POLICY job_qualification_rule_version_scope_policy
ON job_qualification_rule_version
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

COMMENT ON TABLE job_qualification_rule_record IS
    'Durable tenant-scoped Job qualification-rule anchor. It stores no raw rule text or candidate/person data; system-recorded time is PostgreSQL transaction time and closure is bitemporal history, not deletion.';

COMMENT ON TABLE job_qualification_rule_version IS
    'Human-reviewed, evidence-backed Job qualification-rule version. It binds one open rule anchor to the same Job validated Job Analysis snapshot, exact SHA-256 provenance, reviewer and immutable audit/outbox evidence while remaining explicitly unauthorized for candidate or employment decisions until a separate authoritative activation boundary confirms use.';
