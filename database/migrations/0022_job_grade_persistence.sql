-- Persist reviewed enterprise-local Job grade assignments without granting
-- compensation or employment-decision authority. Grade/band definition evidence
-- is immutable; Job assignment truth is bitemporal and remains tenant scoped.

CREATE TABLE job_grade_definition_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    job_grade_definition_record_id uuid PRIMARY KEY,
    grade_code text NOT NULL,
    band_code text NOT NULL,
    grade_band_definition_digest_sha256 text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    CONSTRAINT job_grade_definition_id_operational_check
        CHECK (public.is_operational_uuid(job_grade_definition_record_id)),
    CONSTRAINT job_grade_definition_grade_code_check
        CHECK (grade_code ~ '^[A-Z][A-Z0-9_-]{0,31}$'),
    CONSTRAINT job_grade_definition_band_code_check
        CHECK (band_code ~ '^[A-Z][A-Z0-9_-]{0,31}$'),
    CONSTRAINT job_grade_definition_digest_check
        CHECK (grade_band_definition_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_grade_definition_tenant_identity_unique
        UNIQUE (tenant_record_id, job_grade_definition_record_id),
    CONSTRAINT job_grade_definition_evidence_unique
        UNIQUE (
            tenant_record_id,
            grade_code,
            band_code,
            grade_band_definition_digest_sha256
        )
);

CREATE TABLE job_grade_assignment_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    job_grade_assignment_record_id uuid PRIMARY KEY,
    job_profile_id uuid NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    recorded_to timestamptz,
    CONSTRAINT job_grade_assignment_id_operational_check
        CHECK (public.is_operational_uuid(job_grade_assignment_record_id)),
    CONSTRAINT job_grade_assignment_job_tenant_fk
        FOREIGN KEY (tenant_record_id, job_profile_id)
        REFERENCES job_profile(tenant_record_id, job_profile_id),
    CONSTRAINT job_grade_assignment_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT job_grade_assignment_tenant_identity_unique
        UNIQUE (tenant_record_id, job_grade_assignment_record_id),
    CONSTRAINT job_grade_assignment_job_unique
        UNIQUE (tenant_record_id, job_profile_id)
);

CREATE TABLE job_grade_assignment_version (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    job_grade_assignment_version_id uuid PRIMARY KEY,
    job_grade_assignment_record_id uuid NOT NULL,
    job_grade_definition_record_id uuid NOT NULL,
    analysis_record_id uuid NOT NULL,
    job_analysis_snapshot_digest_sha256 text NOT NULL,
    job_evaluation_method_code text NOT NULL,
    job_evaluation_method_digest_sha256 text NOT NULL,
    review_evidence_json text NOT NULL,
    review_evidence_digest_sha256 text NOT NULL,
    requester_actor_reference text NOT NULL,
    reviewer_actor_reference text NOT NULL,
    purpose_code text NOT NULL DEFAULT 'job_grade_design_review',
    reason_code text NOT NULL,
    evidence_version integer NOT NULL,
    reviewed_at timestamptz NOT NULL,
    review_packet_recorded_at timestamptz NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    recorded_to timestamptz,
    audit_event_record_id uuid NOT NULL,
    review_state text NOT NULL DEFAULT 'reviewed_for_authoritative_resolution',
    job_architecture_state text NOT NULL DEFAULT 'authoritative_job_grade_assignment',
    decision_authority_state text NOT NULL
        DEFAULT 'not_authorized_for_compensation_or_employment_decision',
    human_review_required boolean NOT NULL DEFAULT true,
    CONSTRAINT job_grade_assignment_version_id_operational_check
        CHECK (public.is_operational_uuid(job_grade_assignment_version_id)),
    CONSTRAINT job_grade_assignment_version_record_tenant_fk
        FOREIGN KEY (tenant_record_id, job_grade_assignment_record_id)
        REFERENCES job_grade_assignment_record(
            tenant_record_id,
            job_grade_assignment_record_id
        ),
    CONSTRAINT job_grade_assignment_version_definition_tenant_fk
        FOREIGN KEY (tenant_record_id, job_grade_definition_record_id)
        REFERENCES job_grade_definition_record(
            tenant_record_id,
            job_grade_definition_record_id
        ),
    CONSTRAINT job_grade_assignment_version_analysis_tenant_fk
        FOREIGN KEY (tenant_record_id, analysis_record_id)
        REFERENCES job_analysis_snapshot(tenant_record_id, analysis_record_id),
    CONSTRAINT job_grade_assignment_version_audit_tenant_fk
        FOREIGN KEY (tenant_record_id, audit_event_record_id)
        REFERENCES audit_event_record(tenant_record_id, audit_event_record_id),
    CONSTRAINT job_grade_assignment_snapshot_digest_check
        CHECK (job_analysis_snapshot_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_grade_assignment_method_code_check
        CHECK (
            octet_length(job_evaluation_method_code) BETWEEN 3 AND 64
            AND job_evaluation_method_code ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$'
        ),
    CONSTRAINT job_grade_assignment_method_digest_check
        CHECK (job_evaluation_method_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_grade_assignment_review_evidence_size_check
        CHECK (
            octet_length(review_evidence_json) > 0
            AND octet_length(review_evidence_json) <= 8192
        ),
    CONSTRAINT job_grade_assignment_review_digest_check
        CHECK (review_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_grade_assignment_requester_actor_check
        CHECK (
            requester_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT job_grade_assignment_reviewer_actor_check
        CHECK (
            reviewer_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT job_grade_assignment_actor_separation_check
        CHECK (requester_actor_reference <> reviewer_actor_reference),
    CONSTRAINT job_grade_assignment_purpose_check
        CHECK (purpose_code = 'job_grade_design_review'),
    CONSTRAINT job_grade_assignment_reason_check
        CHECK (reason_code IN (
            'job_architecture_alignment',
            'new_job_design',
            'job_content_change',
            'periodic_job_review'
        )),
    CONSTRAINT job_grade_assignment_evidence_version_check
        CHECK (evidence_version BETWEEN 1 AND 2147483647),
    CONSTRAINT job_grade_assignment_review_chronology_check
        CHECK (reviewed_at <= review_packet_recorded_at),
    CONSTRAINT job_grade_assignment_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT job_grade_assignment_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT job_grade_assignment_review_state_check
        CHECK (review_state = 'reviewed_for_authoritative_resolution'),
    CONSTRAINT job_grade_assignment_architecture_state_check
        CHECK (job_architecture_state = 'authoritative_job_grade_assignment'),
    CONSTRAINT job_grade_assignment_decision_authority_check
        CHECK (
            decision_authority_state =
            'not_authorized_for_compensation_or_employment_decision'
        ),
    CONSTRAINT job_grade_assignment_human_review_check
        CHECK (human_review_required IS TRUE),
    CONSTRAINT job_grade_assignment_version_tenant_identity_unique
        UNIQUE (tenant_record_id, job_grade_assignment_version_id),
    CONSTRAINT job_grade_assignment_audit_event_unique
        UNIQUE (tenant_record_id, audit_event_record_id),
    CONSTRAINT job_grade_assignment_bitemporal_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            job_grade_assignment_record_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE FUNCTION enforce_job_grade_definition_system_time()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.recorded_at IS DISTINCT FROM pg_catalog.transaction_timestamp() THEN
        RAISE EXCEPTION 'Job grade definition recorded_at must equal the current transaction timestamp'
            USING ERRCODE = '22023';
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION enforce_job_grade_definition_system_time() IS
    'Requires PostgreSQL transaction time for immutable enterprise-local Job grade/band definition evidence.';

CREATE TRIGGER job_grade_definition_system_time_guard
BEFORE INSERT ON job_grade_definition_record
FOR EACH ROW
EXECUTE FUNCTION enforce_job_grade_definition_system_time();

CREATE FUNCTION enforce_job_grade_assignment_system_time()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.recorded_to IS NOT NULL THEN
        RAISE EXCEPTION 'Job grade assignment recorded_to must be NULL on insert'
            USING ERRCODE = '22023';
    END IF;
    IF NEW.recorded_from IS DISTINCT FROM pg_catalog.transaction_timestamp() THEN
        RAISE EXCEPTION 'Job grade assignment recorded_from must equal the current transaction timestamp'
            USING ERRCODE = '22023';
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION enforce_job_grade_assignment_system_time() IS
    'Guards new Job-grade assignment anchors and versions: system-recorded time is PostgreSQL transaction time and new recorded intervals begin open.';

CREATE TRIGGER job_grade_assignment_record_system_time_guard
BEFORE INSERT ON job_grade_assignment_record
FOR EACH ROW
EXECUTE FUNCTION enforce_job_grade_assignment_system_time();

CREATE TRIGGER job_grade_assignment_version_system_time_guard
BEFORE INSERT ON job_grade_assignment_version
FOR EACH ROW
EXECUTE FUNCTION enforce_job_grade_assignment_system_time();

CREATE FUNCTION protect_job_grade_definition_immutability()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Job grade definition evidence is immutable; semantic change requires a new definition record'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION protect_job_grade_definition_immutability() IS
    'Rejects UPDATE and DELETE so reviewed enterprise grade/band definition evidence cannot be rewritten in place.';

CREATE TRIGGER job_grade_definition_immutability_guard
BEFORE UPDATE OR DELETE ON job_grade_definition_record
FOR EACH ROW
EXECUTE FUNCTION protect_job_grade_definition_immutability();

CREATE FUNCTION protect_job_grade_assignment_history()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Job grade assignment history cannot be deleted'
            USING ERRCODE = '55000';
    END IF;

    IF OLD.recorded_to IS NOT NULL
       OR NEW.recorded_to IS NULL
       OR NEW.recorded_to IS DISTINCT FROM pg_catalog.transaction_timestamp()
       OR to_jsonb(NEW) - 'recorded_to' <> to_jsonb(OLD) - 'recorded_to' THEN
        RAISE EXCEPTION 'Job grade assignment history may only close an open recorded interval at the current transaction timestamp'
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION protect_job_grade_assignment_history() IS
    'Preserves bitemporal Job-grade evidence: DELETE and in-place rewrites fail closed; the only UPDATE is closing an open recorded interval at PostgreSQL transaction time.';

CREATE TRIGGER job_grade_assignment_record_history_guard
BEFORE UPDATE OR DELETE ON job_grade_assignment_record
FOR EACH ROW
EXECUTE FUNCTION protect_job_grade_assignment_history();

CREATE TRIGGER job_grade_assignment_version_history_guard
BEFORE UPDATE OR DELETE ON job_grade_assignment_version
FOR EACH ROW
EXECUTE FUNCTION protect_job_grade_assignment_history();

CREATE FUNCTION enforce_job_grade_assignment_scope()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    anchor_job_profile_id uuid;
    anchor_recorded_to timestamptz;
    definition_grade_code text;
    definition_band_code text;
    definition_digest text;
    snapshot_job_profile_id uuid;
    snapshot_status_code text;
    snapshot_digest text;
    snapshot_reviewed_by text;
    snapshot_reviewed_at timestamptz;
    review_payload jsonb;
    review_key_count integer;
    computed_review_digest text;
    review_requester text;
    review_reviewer text;
    review_reviewed_at timestamptz;
    review_recorded_at timestamptz;
    audit_event jsonb;
    outbox_found boolean;
BEGIN
    SELECT job_profile_id, recorded_to
    INTO anchor_job_profile_id, anchor_recorded_to
    FROM job_grade_assignment_record
    WHERE tenant_record_id = NEW.tenant_record_id
      AND job_grade_assignment_record_id = NEW.job_grade_assignment_record_id
    FOR SHARE;

    IF NOT FOUND OR anchor_recorded_to IS NOT NULL THEN
        RAISE EXCEPTION 'Job grade assignment version requires an open same-tenant assignment anchor'
            USING ERRCODE = '23514';
    END IF;

    SELECT grade_code, band_code, grade_band_definition_digest_sha256
    INTO definition_grade_code, definition_band_code, definition_digest
    FROM job_grade_definition_record
    WHERE tenant_record_id = NEW.tenant_record_id
      AND job_grade_definition_record_id = NEW.job_grade_definition_record_id
    FOR SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Job grade assignment version requires immutable same-tenant grade definition evidence'
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
        RAISE EXCEPTION 'Job grade assignment version requires a same-tenant Job Analysis snapshot'
            USING ERRCODE = '23514';
    END IF;
    IF snapshot_job_profile_id IS DISTINCT FROM anchor_job_profile_id THEN
        RAISE EXCEPTION 'Job grade assignment and Job Analysis snapshot must resolve to the same Job'
            USING ERRCODE = '23514';
    END IF;
    IF snapshot_status_code <> 'analysis_validated'
       OR snapshot_reviewed_by IS NULL
       OR snapshot_reviewed_at IS NULL THEN
        RAISE EXCEPTION 'Job grade assignment requires a human-reviewed validated Job Analysis snapshot'
            USING ERRCODE = '23514';
    END IF;
    IF snapshot_digest IS DISTINCT FROM NEW.job_analysis_snapshot_digest_sha256 THEN
        RAISE EXCEPTION 'Job grade assignment snapshot digest does not match authoritative Job Analysis evidence'
            USING ERRCODE = '23514';
    END IF;

    computed_review_digest := encode(
        public.digest(
            pg_catalog.convert_to(NEW.review_evidence_json, 'UTF8'),
            'sha256'
        ),
        'hex'
    );
    IF computed_review_digest IS DISTINCT FROM NEW.review_evidence_digest_sha256 THEN
        RAISE EXCEPTION 'Job grade review evidence digest does not match the stored canonical evidence bytes'
            USING ERRCODE = '23514';
    END IF;

    BEGIN
        review_payload := NEW.review_evidence_json::jsonb;
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'canonical Job grade review evidence must be valid JSON'
            USING ERRCODE = '22023';
    END;

    IF pg_catalog.jsonb_typeof(review_payload) IS DISTINCT FROM 'object' THEN
        RAISE EXCEPTION 'canonical Job grade review evidence must be one JSON object'
            USING ERRCODE = '23514';
    END IF;

    SELECT count(*)
    INTO review_key_count
    FROM pg_catalog.jsonb_object_keys(review_payload);

    IF review_key_count <> 19
       OR NOT (
           review_payload ?& ARRAY[
               'band_code',
               'decision_authority',
               'grade_band_definition_digest',
               'grade_code',
               'human_review_required',
               'job_analysis_snapshot_digest',
               'job_analysis_snapshot_reference',
               'job_evaluation_method_code',
               'job_evaluation_method_digest',
               'job_record_reference',
               'next_action',
               'purpose_code',
               'reason_code',
               'recorded_at',
               'requester_actor_reference',
               'review_state',
               'reviewed_at',
               'reviewer_actor_reference',
               'tenant_record_id'
           ]
       ) THEN
        RAISE EXCEPTION 'canonical Job grade review evidence has an unexpected key set'
            USING ERRCODE = '23514';
    END IF;

    BEGIN
        review_reviewed_at := (review_payload ->> 'reviewed_at')::timestamptz;
        review_recorded_at := (review_payload ->> 'recorded_at')::timestamptz;
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'canonical Job grade review evidence timestamps are invalid'
            USING ERRCODE = '22023';
    END;

    review_requester := review_payload ->> 'requester_actor_reference';
    review_reviewer := review_payload ->> 'reviewer_actor_reference';

    IF review_payload ->> 'tenant_record_id' IS DISTINCT FROM NEW.tenant_record_id::text
       OR review_payload ->> 'job_record_reference'
          IS DISTINCT FROM 'job_record:' || anchor_job_profile_id::text
       OR review_payload ->> 'job_analysis_snapshot_reference'
          IS DISTINCT FROM 'job_analysis_snapshot:' || NEW.analysis_record_id::text
       OR review_payload ->> 'job_analysis_snapshot_digest'
          IS DISTINCT FROM NEW.job_analysis_snapshot_digest_sha256
       OR review_payload ->> 'job_evaluation_method_code'
          IS DISTINCT FROM NEW.job_evaluation_method_code
       OR review_payload ->> 'job_evaluation_method_digest'
          IS DISTINCT FROM NEW.job_evaluation_method_digest_sha256
       OR review_payload ->> 'grade_code' IS DISTINCT FROM definition_grade_code
       OR review_payload ->> 'band_code' IS DISTINCT FROM definition_band_code
       OR review_payload ->> 'grade_band_definition_digest'
          IS DISTINCT FROM definition_digest
       OR review_requester IS DISTINCT FROM NEW.requester_actor_reference
       OR review_reviewer IS DISTINCT FROM NEW.reviewer_actor_reference
       OR review_payload ->> 'purpose_code' IS DISTINCT FROM NEW.purpose_code
       OR review_payload ->> 'reason_code' IS DISTINCT FROM NEW.reason_code
       OR review_payload ->> 'review_state' IS DISTINCT FROM NEW.review_state
       OR review_payload ->> 'decision_authority'
          IS DISTINCT FROM 'not_authorized_to_assign_grade_or_compensation'
       OR review_payload ->> 'next_action' IS DISTINCT FROM
          'Within tenant_record_id, re-resolve the authoritative Job and persisted Job Analysis snapshot, verify their exact evidence digest and the reviewed enterprise grade/band definition digest, confirm accountable reviewer authority and human review, then persist any bitemporal Job-grade fact with immutable audit/outbox evidence. This packet does not mutate Job, Position, Assignment, compensation, or any employment decision.'
       OR review_payload -> 'human_review_required' IS DISTINCT FROM 'true'::jsonb
       OR review_reviewed_at IS DISTINCT FROM NEW.reviewed_at
       OR review_recorded_at IS DISTINCT FROM NEW.review_packet_recorded_at
       OR review_requester = review_reviewer THEN
        RAISE EXCEPTION 'canonical Job grade review evidence does not exactly match the proposed assignment scope'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.reviewed_at > NEW.review_packet_recorded_at
       OR NEW.review_packet_recorded_at > NEW.recorded_from THEN
        RAISE EXCEPTION 'Job grade review chronology is inconsistent with persistence system time'
            USING ERRCODE = '23514';
    END IF;

    SELECT canonical_event_json::jsonb
    INTO audit_event
    FROM audit_event_record
    WHERE tenant_record_id = NEW.tenant_record_id
      AND audit_event_record_id = NEW.audit_event_record_id
    FOR SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Job grade assignment requires immutable same-tenant audit evidence'
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
        RAISE EXCEPTION 'Job grade assignment requires transactional audit/outbox evidence'
            USING ERRCODE = '23514';
    END IF;

    IF audit_event ->> 'orgmetrapurpose' <> NEW.purpose_code
       OR audit_event ->> 'orgmetraactor' <> NEW.reviewer_actor_reference
       OR audit_event ->> 'orgmetraevidence' <> NEW.review_evidence_digest_sha256
       OR audit_event ->> 'orgmetrareason' <> NEW.reason_code
       OR audit_event ->> 'subject'
          <> 'job_grade_assignment:' || NEW.job_grade_assignment_record_id::text
       OR audit_event #>> '{data,result_code}' <> NEW.review_state
       OR (audit_event #>> '{data,high_impact}')::boolean IS DISTINCT FROM false
       OR (audit_event ->> 'time')::timestamptz IS DISTINCT FROM NEW.reviewed_at THEN
        RAISE EXCEPTION 'Job grade assignment audit evidence does not exactly match the reviewed design scope'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION enforce_job_grade_assignment_scope() IS
    'Before persisting a Job-grade version, re-resolves its open Job anchor, immutable grade definition, same-Job validated Job Analysis snapshot, exact canonical review packet, reviewer/purpose/reason evidence, and immutable audit/outbox correlation. Persistence does not grant compensation or employment-decision authority.';

CREATE TRIGGER job_grade_assignment_version_scope_guard
BEFORE INSERT ON job_grade_assignment_version
FOR EACH ROW
EXECUTE FUNCTION enforce_job_grade_assignment_scope();

CREATE FUNCTION enforce_job_grade_assignment_anchor_alignment()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.recorded_to IS NULL OR NEW.recorded_to IS NOT DISTINCT FROM OLD.recorded_to THEN
        RETURN NULL;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM job_grade_assignment_version AS version
        WHERE version.tenant_record_id = NEW.tenant_record_id
          AND version.job_grade_assignment_record_id = NEW.job_grade_assignment_record_id
          AND (version.recorded_to IS NULL OR version.recorded_to > NEW.recorded_to)
    ) THEN
        RAISE EXCEPTION 'cannot close Job grade assignment anchor while a recorded version remains open'
            USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION enforce_job_grade_assignment_anchor_alignment() IS
    'Deferred anchor-closure guard: every Job-grade version must be recorded closed no later than its durable Job assignment anchor before commit.';

CREATE CONSTRAINT TRIGGER job_grade_assignment_anchor_alignment_guard
AFTER UPDATE ON job_grade_assignment_record
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION enforce_job_grade_assignment_anchor_alignment();

CREATE FUNCTION reject_job_grade_persistence_truncate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Job grade persistence evidence cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION reject_job_grade_persistence_truncate() IS
    'Rejects table-wide TRUNCATE so immutable Job grade definition and bitemporal assignment evidence cannot bypass row-level history guards.';

CREATE TRIGGER job_grade_definition_truncate_guard
BEFORE TRUNCATE ON job_grade_definition_record
FOR EACH STATEMENT
EXECUTE FUNCTION reject_job_grade_persistence_truncate();

CREATE TRIGGER job_grade_assignment_record_truncate_guard
BEFORE TRUNCATE ON job_grade_assignment_record
FOR EACH STATEMENT
EXECUTE FUNCTION reject_job_grade_persistence_truncate();

CREATE TRIGGER job_grade_assignment_version_truncate_guard
BEFORE TRUNCATE ON job_grade_assignment_version
FOR EACH STATEMENT
EXECUTE FUNCTION reject_job_grade_persistence_truncate();

REVOKE TRUNCATE ON job_grade_definition_record FROM PUBLIC;
REVOKE TRUNCATE ON job_grade_assignment_record FROM PUBLIC;
REVOKE TRUNCATE ON job_grade_assignment_version FROM PUBLIC;

ALTER TABLE job_grade_definition_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_grade_definition_record FORCE ROW LEVEL SECURITY;
CREATE POLICY job_grade_definition_scope_policy
ON job_grade_definition_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE job_grade_assignment_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_grade_assignment_record FORCE ROW LEVEL SECURITY;
CREATE POLICY job_grade_assignment_record_scope_policy
ON job_grade_assignment_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE job_grade_assignment_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_grade_assignment_version FORCE ROW LEVEL SECURITY;
CREATE POLICY job_grade_assignment_version_scope_policy
ON job_grade_assignment_version
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

COMMENT ON TABLE job_grade_definition_record IS
    'Immutable tenant-scoped enterprise-local Job grade/band definition evidence. Semantic change creates a new definition record; this relation grants no compensation or employment-decision authority.';

COMMENT ON TABLE job_grade_assignment_record IS
    'Durable tenant-scoped bitemporal Job-grade assignment anchor. One stable anchor is owned by one authoritative Job and system-recorded history is correction-not-rewrite.';

COMMENT ON TABLE job_grade_assignment_version IS
    'Human-reviewed bitemporal Job-grade assignment version bound to one immutable grade definition, same-Job validated Job Analysis snapshot, exact canonical JobGradeDesignReviewPacket bytes, and immutable audit/outbox evidence. It remains explicitly unauthorized for compensation or employment decisions.';
