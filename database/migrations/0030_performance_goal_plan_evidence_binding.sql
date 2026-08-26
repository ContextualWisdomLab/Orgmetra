-- Bind normalized performance-goal persistence to the exact value-minimized
-- plan and activation evidence produced by PRs #92/#121. This closes a gap in
-- migration 0029 where syntactically valid digests could be supplied independently
-- of the normalized goal-set, Job, Employment, cycle and approving-actor fields.

ALTER TABLE performance_goal_plan_version
    ADD COLUMN plan_evidence_json text NOT NULL,
    ADD COLUMN activation_evidence_json text NOT NULL,
    ADD CONSTRAINT performance_goal_plan_plan_evidence_size_check
        CHECK (octet_length(plan_evidence_json) BETWEEN 2 AND 8192),
    ADD CONSTRAINT performance_goal_plan_activation_evidence_size_check
        CHECK (octet_length(activation_evidence_json) BETWEEN 2 AND 4096);

CREATE FUNCTION validate_performance_goal_plan_evidence_binding()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    anchor_plan_reference text;
    anchor_employment_id uuid;
    anchor_job_profile_id uuid;
    anchor_cycle_reference text;
    plan_evidence jsonb;
    activation_evidence jsonb;
    plan_keys text[];
    activation_keys text[];
    plan_generated_at timestamptz;
    activation_approved_at timestamptz;
    activation_activated_at timestamptz;
    expected_plan_keys constant text[] := ARRAY[
        'contains_employment_decision',
        'contains_goal_text',
        'contains_performance_rating',
        'decision_authority',
        'employment_decision_authority',
        'employment_record_reference',
        'evidence_version',
        'feedback_cadence_code',
        'generated_at',
        'goal_count',
        'goal_set_digest',
        'human_review_required',
        'job_profile_reference',
        'measurement_definition_digest',
        'next_action',
        'performance_cycle_reference',
        'performance_goal_plan_reference',
        'purpose_code',
        'reason_code',
        'requester_reference',
        'review_state',
        'reviewer_reference',
        'tenant_record_id'
    ];
    expected_activation_keys constant text[] := ARRAY[
        'activated_at',
        'activation_reference',
        'activation_state',
        'approved_at',
        'approving_actor_reference',
        'authority_evidence_digest',
        'authority_evidence_reference',
        'employment_decision_authority',
        'evidence_version',
        'performance_goal_plan_reference',
        'plan_digest',
        'rating_authority',
        'tenant_record_id'
    ];
BEGIN
    IF encode(
        public.digest(pg_catalog.convert_to(NEW.plan_evidence_json, 'UTF8'), 'sha256'),
        'hex'
    ) <> NEW.plan_evidence_digest_sha256 THEN
        RAISE EXCEPTION 'performance-goal plan evidence digest does not match exact evidence bytes'
            USING ERRCODE = '23514';
    END IF;
    IF encode(
        public.digest(pg_catalog.convert_to(NEW.activation_evidence_json, 'UTF8'), 'sha256'),
        'hex'
    ) <> NEW.activation_evidence_digest_sha256 THEN
        RAISE EXCEPTION 'performance-goal activation evidence digest does not match exact evidence bytes'
            USING ERRCODE = '23514';
    END IF;

    BEGIN
        plan_evidence := NEW.plan_evidence_json::jsonb;
        activation_evidence := NEW.activation_evidence_json::jsonb;
    EXCEPTION
        WHEN others THEN
            RAISE EXCEPTION 'performance-goal persisted evidence must be valid JSON'
                USING ERRCODE = '22023';
    END;

    IF jsonb_typeof(plan_evidence) <> 'object'
       OR jsonb_typeof(activation_evidence) <> 'object' THEN
        RAISE EXCEPTION 'performance-goal persisted evidence must be JSON objects'
            USING ERRCODE = '22023';
    END IF;

    SELECT array_agg(evidence_key ORDER BY evidence_key COLLATE "C")
    INTO plan_keys
    FROM jsonb_object_keys(plan_evidence) AS key_set(evidence_key);
    SELECT array_agg(evidence_key ORDER BY evidence_key COLLATE "C")
    INTO activation_keys
    FROM jsonb_object_keys(activation_evidence) AS key_set(evidence_key);

    IF plan_keys IS DISTINCT FROM expected_plan_keys THEN
        RAISE EXCEPTION 'performance-goal plan evidence has an unexpected canonical key set'
            USING ERRCODE = '23514';
    END IF;
    IF activation_keys IS DISTINCT FROM expected_activation_keys THEN
        RAISE EXCEPTION 'performance-goal activation evidence has an unexpected canonical key set'
            USING ERRCODE = '23514';
    END IF;

    SELECT performance_goal_plan_reference, employment_record_id, job_profile_id,
           performance_cycle_reference
    INTO anchor_plan_reference, anchor_employment_id, anchor_job_profile_id,
         anchor_cycle_reference
    FROM performance_goal_plan_record
    WHERE tenant_record_id = NEW.tenant_record_id
      AND performance_goal_plan_record_id = NEW.performance_goal_plan_record_id
    FOR SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'performance-goal evidence requires a same-tenant plan anchor'
            USING ERRCODE = '23514';
    END IF;

    IF jsonb_typeof(plan_evidence -> 'contains_employment_decision') <> 'boolean'
       OR (plan_evidence ->> 'contains_employment_decision')::boolean IS DISTINCT FROM false
       OR jsonb_typeof(plan_evidence -> 'contains_goal_text') <> 'boolean'
       OR (plan_evidence ->> 'contains_goal_text')::boolean IS DISTINCT FROM false
       OR jsonb_typeof(plan_evidence -> 'contains_performance_rating') <> 'boolean'
       OR (plan_evidence ->> 'contains_performance_rating')::boolean IS DISTINCT FROM false
       OR jsonb_typeof(plan_evidence -> 'human_review_required') <> 'boolean'
       OR (plan_evidence ->> 'human_review_required')::boolean IS DISTINCT FROM true
       OR plan_evidence ->> 'decision_authority' <> 'not_authorized_for_performance_rating'
       OR plan_evidence ->> 'employment_decision_authority' <> 'not_authorized_for_employment_decision'
       OR plan_evidence ->> 'review_state' <> 'requires_human_review'
       OR plan_evidence ->> 'purpose_code' <> 'performance_goal_plan_review'
       OR plan_evidence ->> 'reason_code' <> 'goal_plan_activation_review'
       OR plan_evidence ->> 'tenant_record_id' <> NEW.tenant_record_id::text
       OR plan_evidence ->> 'performance_goal_plan_reference' <> anchor_plan_reference
       OR plan_evidence ->> 'employment_record_reference' <> 'employment_record:' || anchor_employment_id::text
       OR plan_evidence ->> 'job_profile_reference' <> 'job_profile:' || anchor_job_profile_id::text
       OR plan_evidence ->> 'performance_cycle_reference' <> anchor_cycle_reference
       OR plan_evidence ->> 'goal_set_digest' <> NEW.goal_set_digest_sha256
       OR plan_evidence ->> 'measurement_definition_digest' <> NEW.measurement_definition_digest_sha256
       OR plan_evidence ->> 'feedback_cadence_code' <> NEW.feedback_cadence_code
       OR plan_evidence ->> 'reviewer_reference' <> NEW.approving_actor_reference
       OR plan_evidence ->> 'requester_reference' = NEW.approving_actor_reference
       OR jsonb_typeof(plan_evidence -> 'goal_count') <> 'number'
       OR (plan_evidence ->> 'goal_count')::integer IS DISTINCT FROM NEW.goal_count
       OR jsonb_typeof(plan_evidence -> 'evidence_version') <> 'number'
       OR (plan_evidence ->> 'evidence_version')::integer NOT BETWEEN 1 AND 2147483647
       OR jsonb_typeof(plan_evidence -> 'generated_at') <> 'string'
       OR jsonb_typeof(plan_evidence -> 'next_action') <> 'string' THEN
        RAISE EXCEPTION 'performance-goal plan evidence does not match the normalized persisted scope'
            USING ERRCODE = '23514';
    END IF;

    BEGIN
        plan_generated_at := (plan_evidence ->> 'generated_at')::timestamptz;
    EXCEPTION
        WHEN others THEN
            RAISE EXCEPTION 'performance-goal plan generated_at is invalid'
                USING ERRCODE = '22023';
    END;
    IF plan_generated_at > NEW.approved_at THEN
        RAISE EXCEPTION 'performance-goal plan evidence cannot be approved before it was generated'
            USING ERRCODE = '23514';
    END IF;

    IF activation_evidence ->> 'tenant_record_id' <> NEW.tenant_record_id::text
       OR activation_evidence ->> 'performance_goal_plan_reference' <> anchor_plan_reference
       OR activation_evidence ->> 'plan_digest' <> NEW.plan_evidence_digest_sha256
       OR activation_evidence ->> 'activation_reference' <> NEW.activation_reference
       OR activation_evidence ->> 'approving_actor_reference' <> NEW.approving_actor_reference
       OR activation_evidence ->> 'authority_evidence_reference' <> NEW.authority_evidence_reference
       OR activation_evidence ->> 'authority_evidence_digest' <> NEW.authority_evidence_digest_sha256
       OR activation_evidence ->> 'activation_state' <> 'authoritatively_activated'
       OR activation_evidence ->> 'rating_authority' <> 'not_authorized_for_performance_rating'
       OR activation_evidence ->> 'employment_decision_authority' <> 'not_authorized_for_employment_decision'
       OR jsonb_typeof(activation_evidence -> 'evidence_version') <> 'number'
       OR (activation_evidence ->> 'evidence_version')::integer IS DISTINCT FROM 1
       OR jsonb_typeof(activation_evidence -> 'approved_at') <> 'string'
       OR jsonb_typeof(activation_evidence -> 'activated_at') <> 'string' THEN
        RAISE EXCEPTION 'performance-goal activation evidence does not match the normalized persisted scope'
            USING ERRCODE = '23514';
    END IF;

    BEGIN
        activation_approved_at := (activation_evidence ->> 'approved_at')::timestamptz;
        activation_activated_at := (activation_evidence ->> 'activated_at')::timestamptz;
    EXCEPTION
        WHEN others THEN
            RAISE EXCEPTION 'performance-goal activation evidence contains invalid timestamps'
                USING ERRCODE = '22023';
    END;
    IF activation_approved_at IS DISTINCT FROM NEW.approved_at
       OR activation_activated_at IS DISTINCT FROM NEW.activated_at THEN
        RAISE EXCEPTION 'performance-goal activation timestamps do not match persisted chronology'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION validate_performance_goal_plan_evidence_binding() IS
    'Recomputes exact SHA-256 over the value-minimized PR #92/#121 evidence bytes and requires their tenant/Employment/Job/cycle/digest/actor/time scope to equal the normalized plan version before persistence.';

CREATE TRIGGER performance_goal_plan_evidence_binding_guard
BEFORE INSERT ON performance_goal_plan_version
FOR EACH ROW
EXECUTE FUNCTION validate_performance_goal_plan_evidence_binding();
