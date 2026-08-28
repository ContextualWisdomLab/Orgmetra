-- Persist human-reviewed Employment work-capacity truth without inventing payroll,
-- leave, scheduling, disability, or compensation truth. The parent review packet is
-- non-authorizing; this migration adds a distinct authoritative HRIS application
-- boundary. Audit/outbox identifiers are opaque published-contract correlations.
-- This migration does not query another service's application tables.

CREATE TABLE employment_work_capacity_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    employment_work_capacity_record_id uuid PRIMARY KEY,
    employment_record_id uuid NOT NULL,
    created_by_actor_reference text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),

    CONSTRAINT employment_work_capacity_record_id_operational_check
        CHECK (public.is_operational_uuid(employment_work_capacity_record_id)),
    CONSTRAINT employment_work_capacity_employment_tenant_fk
        FOREIGN KEY (tenant_record_id, employment_record_id)
        REFERENCES employment_record(tenant_record_id, employment_record_id),
    CONSTRAINT employment_work_capacity_created_actor_check
        CHECK (
            created_by_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT employment_work_capacity_record_tenant_identity_unique
        UNIQUE (tenant_record_id, employment_work_capacity_record_id),
    CONSTRAINT employment_work_capacity_single_anchor_unique
        UNIQUE (tenant_record_id, employment_record_id)
);

COMMENT ON TABLE employment_work_capacity_record IS
    'Stable tenant-qualified identity for authoritative Employment work-capacity truth. It contains no medical, payroll, compensation, rating, candidate, or free-form reason data.';

CREATE TABLE employment_work_capacity_version (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    employment_work_capacity_version_id uuid PRIMARY KEY,
    employment_work_capacity_record_id uuid NOT NULL,
    current_capacity_ratio numeric(5,4) NOT NULL,
    capacity_ratio numeric(5,4) NOT NULL,
    effective_on date NOT NULL,
    review_evidence_json text NOT NULL,
    review_evidence_digest_sha256 text NOT NULL,
    employment_terms_evidence_digest_sha256 text NOT NULL,
    capacity_policy_evidence_digest_sha256 text NOT NULL,
    reviewer_identity_evidence_digest_sha256 text NOT NULL,
    requester_actor_reference text NOT NULL,
    reviewer_actor_reference text NOT NULL,
    applied_by_actor_reference text NOT NULL,
    reason_code text NOT NULL,
    reviewed_at timestamptz NOT NULL,
    review_recorded_at timestamptz NOT NULL,
    review_audit_event_reference text NOT NULL,
    review_audit_envelope_digest_sha256 text NOT NULL,
    application_audit_event_reference text NOT NULL,
    application_outbox_event_reference text NOT NULL,
    application_audit_envelope_digest_sha256 text NOT NULL,
    prior_capacity_match_state text NOT NULL,
    application_purpose_code text NOT NULL DEFAULT 'employment_work_capacity_change',
    decision_authority_state text NOT NULL DEFAULT 'human_reviewed_authoritative_hris_truth',
    evidence_version integer NOT NULL DEFAULT 1,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    recorded_to timestamptz,

    CONSTRAINT employment_work_capacity_version_id_operational_check
        CHECK (public.is_operational_uuid(employment_work_capacity_version_id)),
    CONSTRAINT employment_work_capacity_version_record_tenant_fk
        FOREIGN KEY (tenant_record_id, employment_work_capacity_record_id)
        REFERENCES employment_work_capacity_record(tenant_record_id, employment_work_capacity_record_id),
    CONSTRAINT employment_work_capacity_current_ratio_check
        CHECK (current_capacity_ratio >= 0.0000 AND current_capacity_ratio <= 1.0000),
    CONSTRAINT employment_work_capacity_ratio_check
        CHECK (capacity_ratio >= 0.0000 AND capacity_ratio <= 1.0000),
    CONSTRAINT employment_work_capacity_change_required_check
        CHECK (capacity_ratio <> current_capacity_ratio),
    CONSTRAINT employment_work_capacity_review_digest_check
        CHECK (review_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT employment_work_capacity_terms_digest_check
        CHECK (employment_terms_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT employment_work_capacity_policy_digest_check
        CHECK (capacity_policy_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT employment_work_capacity_reviewer_identity_digest_check
        CHECK (reviewer_identity_evidence_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT employment_work_capacity_requester_actor_check
        CHECK (
            requester_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT employment_work_capacity_reviewer_actor_check
        CHECK (
            reviewer_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT employment_work_capacity_applier_actor_check
        CHECK (
            applied_by_actor_reference ~
            '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT employment_work_capacity_actor_separation_check
        CHECK (
            requester_actor_reference <> reviewer_actor_reference
            AND applied_by_actor_reference <> requester_actor_reference
            AND applied_by_actor_reference <> reviewer_actor_reference
        ),
    CONSTRAINT employment_work_capacity_reason_code_check
        CHECK (
            reason_code IN (
                'employee_agreed_change',
                'contractual_hours_change',
                'business_schedule_change',
                'return_from_leave'
            )
        ),
    CONSTRAINT employment_work_capacity_review_chronology_check
        CHECK (reviewed_at <= review_recorded_at AND review_recorded_at <= recorded_from),
    CONSTRAINT employment_work_capacity_review_audit_reference_check
        CHECK (
            review_audit_event_reference ~
            '^audit_event:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT employment_work_capacity_review_audit_digest_check
        CHECK (review_audit_envelope_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT employment_work_capacity_application_audit_reference_check
        CHECK (
            application_audit_event_reference ~
            '^audit_event:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT employment_work_capacity_application_outbox_reference_check
        CHECK (
            application_outbox_event_reference ~
            '^outbox_event:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT employment_work_capacity_application_audit_digest_check
        CHECK (application_audit_envelope_digest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT employment_work_capacity_prior_match_state_check
        CHECK (
            prior_capacity_match_state IN (
                'bootstrap_from_reviewed_terms',
                'matched_authoritative_capacity'
            )
        ),
    CONSTRAINT employment_work_capacity_application_purpose_check
        CHECK (application_purpose_code = 'employment_work_capacity_change'),
    CONSTRAINT employment_work_capacity_decision_authority_check
        CHECK (decision_authority_state = 'human_reviewed_authoritative_hris_truth'),
    CONSTRAINT employment_work_capacity_evidence_version_check
        CHECK (evidence_version = 1),
    CONSTRAINT employment_work_capacity_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT employment_work_capacity_version_tenant_identity_unique
        UNIQUE (tenant_record_id, employment_work_capacity_version_id),
    CONSTRAINT employment_work_capacity_bitemporal_point_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            employment_work_capacity_record_id WITH =,
            effective_on WITH =,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

COMMENT ON TABLE employment_work_capacity_version IS
    'Effective-dated, system-versioned Employment capacity truth. Business state at a date is the latest effective_on not after that date among versions visible at known_at.';

CREATE FUNCTION enforce_employment_work_capacity_anchor_system_time()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.created_at IS DISTINCT FROM pg_catalog.transaction_timestamp() THEN
        RAISE EXCEPTION 'Employment work-capacity created_at must equal transaction time'
            USING ERRCODE = '22023';
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION enforce_employment_work_capacity_anchor_system_time() IS
    'Prevents caller-backdated system creation time on the stable Employment work-capacity identity.';

CREATE TRIGGER employment_work_capacity_anchor_system_time_guard
BEFORE INSERT ON employment_work_capacity_record
FOR EACH ROW
EXECUTE FUNCTION enforce_employment_work_capacity_anchor_system_time();

CREATE FUNCTION resolve_employment_work_capacity(
    requested_tenant_id uuid,
    requested_employment_id uuid,
    requested_effective_on date,
    requested_known_at timestamptz
)
RETURNS numeric(5,4)
LANGUAGE sql
STABLE
AS $$
    SELECT capacity_version.capacity_ratio
    FROM employment_work_capacity_record AS capacity_record
    JOIN employment_work_capacity_version AS capacity_version
      ON capacity_version.tenant_record_id = capacity_record.tenant_record_id
     AND capacity_version.employment_work_capacity_record_id =
         capacity_record.employment_work_capacity_record_id
    WHERE capacity_record.tenant_record_id = requested_tenant_id
      AND capacity_record.employment_record_id = requested_employment_id
      AND capacity_version.effective_on <= requested_effective_on
      AND capacity_version.recorded_from <= requested_known_at
      AND (
          capacity_version.recorded_to IS NULL
          OR capacity_version.recorded_to > requested_known_at
      )
    ORDER BY capacity_version.effective_on DESC, capacity_version.recorded_from DESC
    LIMIT 1
$$;

COMMENT ON FUNCTION resolve_employment_work_capacity(uuid, uuid, date, timestamptz) IS
    'Resolves authoritative Employment work capacity at one business date and system-knowledge coordinate. Callers still require purpose-bound read authorization.';

REVOKE ALL ON FUNCTION resolve_employment_work_capacity(uuid, uuid, date, timestamptz) FROM PUBLIC;

CREATE FUNCTION validate_employment_work_capacity_version_insert()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    insertion_time timestamptz := pg_catalog.transaction_timestamp();
    anchor_employment_id uuid;
    review_json json;
    review_payload jsonb;
    observed_keys text[];
    expected_keys constant text[] := ARRAY[
        'capacity_policy_evidence_digest',
        'current_capacity_ratio',
        'decision_authority',
        'effective_on',
        'employment_record_reference',
        'employment_terms_evidence_digest',
        'evidence_version',
        'human_review_required',
        'next_action',
        'proposed_capacity_ratio',
        'purpose_code',
        'reason_code',
        'recorded_at',
        'requester_actor_reference',
        'review_state',
        'reviewed_at',
        'reviewer_actor_reference',
        'reviewer_identity_evidence_digest',
        'tenant_record_id'
    ];
    computed_review_digest text;
    reviewed_time timestamptz;
    review_recorded_time timestamptz;
    authoritative_current numeric(5,4);
    expected_next_action constant text := 'Within tenant_record_id, re-resolve the authoritative Employment and current work-capacity truth at effective_on, verify reviewer identity/authority and the exact reviewed employment-terms and capacity-policy evidence, recalculate Assignment allocation and compensation/payroll impacts, then persist any approved bitemporal capacity change with immutable audit/outbox evidence. This packet does not itself mutate Employment, Assignment, compensation, payroll, leave, or scheduling.';
BEGIN
    IF NEW.recorded_from IS DISTINCT FROM insertion_time OR NEW.recorded_to IS NOT NULL THEN
        RAISE EXCEPTION 'Employment work-capacity recorded_from must equal transaction time and recorded_to must start open'
            USING ERRCODE = '22023';
    END IF;

    computed_review_digest := pg_catalog.encode(
        public.digest(pg_catalog.convert_to(NEW.review_evidence_json, 'UTF8'), 'sha256'),
        'hex'
    );
    IF computed_review_digest IS DISTINCT FROM NEW.review_evidence_digest_sha256 THEN
        RAISE EXCEPTION 'review evidence digest does not match exact JSON bytes'
            USING ERRCODE = '22023';
    END IF;

    BEGIN
        review_json := NEW.review_evidence_json::json;
        review_payload := NEW.review_evidence_json::jsonb;
    EXCEPTION WHEN others THEN
        RAISE EXCEPTION 'review evidence must be valid JSON'
            USING ERRCODE = '22023';
    END;

    IF pg_catalog.json_typeof(review_json) <> 'object' THEN
        RAISE EXCEPTION 'review evidence must be one JSON object'
            USING ERRCODE = '22023';
    END IF;

    SELECT pg_catalog.array_agg(review_key ORDER BY review_key COLLATE "C")
    INTO observed_keys
    FROM pg_catalog.json_each(review_json) AS item(review_key, review_value);

    IF observed_keys IS DISTINCT FROM expected_keys THEN
        RAISE EXCEPTION 'review evidence has an unexpected canonical key set'
            USING ERRCODE = '22023';
    END IF;

    IF review_payload->>'tenant_record_id' IS DISTINCT FROM NEW.tenant_record_id::text THEN
        RAISE EXCEPTION 'review tenant does not match requested tenant'
            USING ERRCODE = '22023';
    END IF;

    SELECT capacity_record.employment_record_id
    INTO anchor_employment_id
    FROM employment_work_capacity_record AS capacity_record
    WHERE capacity_record.tenant_record_id = NEW.tenant_record_id
      AND capacity_record.employment_work_capacity_record_id =
          NEW.employment_work_capacity_record_id;

    IF anchor_employment_id IS NULL THEN
        RAISE EXCEPTION 'Employment work-capacity anchor is missing from the requested tenant'
            USING ERRCODE = '23503';
    END IF;

    IF review_payload->>'employment_record_reference' IS DISTINCT FROM
       'employment_record:' || anchor_employment_id::text THEN
        RAISE EXCEPTION 'review Employment reference does not match the capacity anchor'
            USING ERRCODE = '22023';
    END IF;

    IF pg_catalog.jsonb_typeof(review_payload->'current_capacity_ratio') <> 'string'
       OR review_payload->>'current_capacity_ratio' !~ '^(0\.[0-9]{4}|1\.0000)$'
       OR (review_payload->>'current_capacity_ratio')::numeric(5,4) IS DISTINCT FROM
          NEW.current_capacity_ratio THEN
        RAISE EXCEPTION 'review current capacity is noncanonical or mismatched'
            USING ERRCODE = '22023';
    END IF;

    IF pg_catalog.jsonb_typeof(review_payload->'proposed_capacity_ratio') <> 'string'
       OR review_payload->>'proposed_capacity_ratio' !~ '^(0\.[0-9]{4}|1\.0000)$'
       OR (review_payload->>'proposed_capacity_ratio')::numeric(5,4) IS DISTINCT FROM
          NEW.capacity_ratio THEN
        RAISE EXCEPTION 'review proposed capacity is noncanonical or mismatched'
            USING ERRCODE = '22023';
    END IF;

    IF review_payload->>'effective_on' IS DISTINCT FROM NEW.effective_on::text THEN
        RAISE EXCEPTION 'review effective date does not match persisted capacity truth'
            USING ERRCODE = '22023';
    END IF;

    IF review_payload->>'employment_terms_evidence_digest' IS DISTINCT FROM
       NEW.employment_terms_evidence_digest_sha256
       OR review_payload->>'capacity_policy_evidence_digest' IS DISTINCT FROM
          NEW.capacity_policy_evidence_digest_sha256
       OR review_payload->>'reviewer_identity_evidence_digest' IS DISTINCT FROM
          NEW.reviewer_identity_evidence_digest_sha256 THEN
        RAISE EXCEPTION 'review evidence digests do not match normalized persistence evidence'
            USING ERRCODE = '22023';
    END IF;

    IF review_payload->>'requester_actor_reference' IS DISTINCT FROM NEW.requester_actor_reference
       OR review_payload->>'reviewer_actor_reference' IS DISTINCT FROM NEW.reviewer_actor_reference
       OR review_payload->>'reason_code' IS DISTINCT FROM NEW.reason_code THEN
        RAISE EXCEPTION 'review actors or reason do not match normalized persistence evidence'
            USING ERRCODE = '22023';
    END IF;

    IF review_payload->>'purpose_code' IS DISTINCT FROM 'employment_work_capacity_review'
       OR review_payload->>'review_state' IS DISTINCT FROM 'reviewed_for_authoritative_resolution'
       OR review_payload->>'decision_authority' IS DISTINCT FROM
          'not_authorized_to_change_employment_or_compensation'
       OR pg_catalog.jsonb_typeof(review_payload->'human_review_required') <> 'boolean'
       OR (review_payload->>'human_review_required')::boolean IS NOT TRUE
       OR pg_catalog.jsonb_typeof(review_payload->'evidence_version') <> 'number'
       OR review_payload->>'evidence_version' IS DISTINCT FROM '1'
       OR review_payload->>'next_action' IS DISTINCT FROM expected_next_action THEN
        RAISE EXCEPTION 'review governance state is unsupported or noncanonical'
            USING ERRCODE = '22023';
    END IF;

    IF review_payload->>'reviewed_at' !~
       '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$'
       OR review_payload->>'recorded_at' !~
          '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$' THEN
        RAISE EXCEPTION 'review timestamps must be canonical UTC RFC 3339 text'
            USING ERRCODE = '22023';
    END IF;

    reviewed_time := (review_payload->>'reviewed_at')::timestamptz;
    review_recorded_time := (review_payload->>'recorded_at')::timestamptz;
    IF reviewed_time IS DISTINCT FROM NEW.reviewed_at
       OR review_recorded_time IS DISTINCT FROM NEW.review_recorded_at
       OR reviewed_time > review_recorded_time
       OR review_recorded_time > insertion_time THEN
        RAISE EXCEPTION 'review chronology is invalid or does not match normalized evidence'
            USING ERRCODE = '22023';
    END IF;

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(
            NEW.tenant_record_id::text || ':' || anchor_employment_id::text,
            0
        )
    );

    IF NOT EXISTS (
        SELECT 1
        FROM employment_record_version AS employment_version
        WHERE employment_version.tenant_record_id = NEW.tenant_record_id
          AND employment_version.employment_record_id = anchor_employment_id
          AND employment_version.employment_status_code IN ('active', 'leave')
          AND employment_version.effective_from <= NEW.effective_on
          AND (
              employment_version.effective_to IS NULL
              OR employment_version.effective_to > NEW.effective_on
          )
          AND employment_version.recorded_from <= insertion_time
          AND (
              employment_version.recorded_to IS NULL
              OR employment_version.recorded_to > insertion_time
          )
    ) THEN
        RAISE EXCEPTION 'Employment work-capacity requires active or leave Employment truth at effective_on'
            USING ERRCODE = '23514';
    END IF;

    authoritative_current := resolve_employment_work_capacity(
        NEW.tenant_record_id,
        anchor_employment_id,
        NEW.effective_on,
        insertion_time
    );

    IF authoritative_current IS NULL THEN
        NEW.prior_capacity_match_state := 'bootstrap_from_reviewed_terms';
    ELSIF authoritative_current IS DISTINCT FROM NEW.current_capacity_ratio THEN
        RAISE EXCEPTION 'reviewed current capacity does not match authoritative capacity'
            USING ERRCODE = '23514';
    ELSE
        NEW.prior_capacity_match_state := 'matched_authoritative_capacity';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION validate_employment_work_capacity_version_insert() IS
    'Revalidates exact reviewed evidence, same-tenant Employment scope, human actor separation, system time, staffable Employment status, and prior authoritative capacity before persistence.';

CREATE TRIGGER employment_work_capacity_version_insert_guard
BEFORE INSERT ON employment_work_capacity_version
FOR EACH ROW
EXECUTE FUNCTION validate_employment_work_capacity_version_insert();

CREATE FUNCTION apply_employment_work_capacity_change(
    requested_tenant_id uuid,
    requested_capacity_record_id uuid,
    requested_capacity_version_id uuid,
    requested_employment_id uuid,
    requested_review_evidence_json text,
    requested_review_evidence_digest_sha256 text,
    requested_review_audit_event_reference text,
    requested_review_audit_envelope_digest_sha256 text,
    requested_applied_by_actor_reference text,
    requested_application_audit_event_reference text,
    requested_application_outbox_event_reference text,
    requested_application_audit_envelope_digest_sha256 text
)
RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
    session_tenant_id uuid;
    review_payload jsonb;
    existing_capacity_record_id uuid;
    proposed_capacity numeric(5,4);
    current_capacity numeric(5,4);
    requested_effective_on date;
BEGIN
    session_tenant_id := NULLIF(
        pg_catalog.current_setting('orgmetra.tenant_record_id', true),
        ''
    )::uuid;
    IF session_tenant_id IS DISTINCT FROM requested_tenant_id THEN
        RAISE EXCEPTION 'tenant context does not match requested tenant'
            USING ERRCODE = '42501';
    END IF;

    IF NOT public.is_operational_uuid(requested_tenant_id)
       OR NOT public.is_operational_uuid(requested_capacity_record_id)
       OR NOT public.is_operational_uuid(requested_capacity_version_id)
       OR NOT public.is_operational_uuid(requested_employment_id) THEN
        RAISE EXCEPTION 'Employment work-capacity application requires operational UUID identifiers'
            USING ERRCODE = '22023';
    END IF;

    IF requested_review_evidence_digest_sha256 !~ '^[0-9a-f]{64}$'
       OR pg_catalog.encode(
              public.digest(pg_catalog.convert_to(requested_review_evidence_json, 'UTF8'), 'sha256'),
              'hex'
          ) IS DISTINCT FROM requested_review_evidence_digest_sha256 THEN
        RAISE EXCEPTION 'review evidence digest does not match exact JSON bytes'
            USING ERRCODE = '22023';
    END IF;

    BEGIN
        review_payload := requested_review_evidence_json::jsonb;
    EXCEPTION WHEN others THEN
        RAISE EXCEPTION 'review evidence must be valid JSON'
            USING ERRCODE = '22023';
    END;

    IF review_payload->>'tenant_record_id' IS DISTINCT FROM requested_tenant_id::text THEN
        RAISE EXCEPTION 'review tenant does not match requested tenant'
            USING ERRCODE = '22023';
    END IF;
    IF review_payload->>'employment_record_reference' IS DISTINCT FROM
       'employment_record:' || requested_employment_id::text THEN
        RAISE EXCEPTION 'review Employment reference does not match requested Employment'
            USING ERRCODE = '22023';
    END IF;

    IF requested_applied_by_actor_reference !~
       '^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
       OR requested_applied_by_actor_reference = review_payload->>'requester_actor_reference'
       OR requested_applied_by_actor_reference = review_payload->>'reviewer_actor_reference' THEN
        RAISE EXCEPTION 'applier must differ from requester and reviewer'
            USING ERRCODE = '22023';
    END IF;

    IF requested_review_audit_event_reference !~
       '^audit_event:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
       OR requested_application_audit_event_reference !~
          '^audit_event:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
       OR requested_application_outbox_event_reference !~
          '^outbox_event:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
       OR requested_review_audit_envelope_digest_sha256 !~ '^[0-9a-f]{64}$'
       OR requested_application_audit_envelope_digest_sha256 !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'audit/outbox evidence correlations are malformed'
            USING ERRCODE = '22023';
    END IF;

    IF review_payload->>'current_capacity_ratio' !~ '^(0\.[0-9]{4}|1\.0000)$'
       OR review_payload->>'proposed_capacity_ratio' !~ '^(0\.[0-9]{4}|1\.0000)$' THEN
        RAISE EXCEPTION 'review capacity ratios are noncanonical'
            USING ERRCODE = '22023';
    END IF;

    current_capacity := (review_payload->>'current_capacity_ratio')::numeric(5,4);
    proposed_capacity := (review_payload->>'proposed_capacity_ratio')::numeric(5,4);
    requested_effective_on := (review_payload->>'effective_on')::date;

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(
            requested_tenant_id::text || ':' || requested_employment_id::text,
            0
        )
    );

    SELECT capacity_record.employment_work_capacity_record_id
    INTO existing_capacity_record_id
    FROM employment_work_capacity_record AS capacity_record
    WHERE capacity_record.tenant_record_id = requested_tenant_id
      AND capacity_record.employment_record_id = requested_employment_id;

    IF existing_capacity_record_id IS NULL THEN
        INSERT INTO employment_work_capacity_record (
            tenant_record_id,
            employment_work_capacity_record_id,
            employment_record_id,
            created_by_actor_reference
        ) VALUES (
            requested_tenant_id,
            requested_capacity_record_id,
            requested_employment_id,
            requested_applied_by_actor_reference
        );
        existing_capacity_record_id := requested_capacity_record_id;
    ELSIF existing_capacity_record_id IS DISTINCT FROM requested_capacity_record_id THEN
        RAISE EXCEPTION 'requested work-capacity anchor does not match authoritative Employment anchor'
            USING ERRCODE = '23514';
    END IF;

    INSERT INTO employment_work_capacity_version (
        tenant_record_id,
        employment_work_capacity_version_id,
        employment_work_capacity_record_id,
        current_capacity_ratio,
        capacity_ratio,
        effective_on,
        review_evidence_json,
        review_evidence_digest_sha256,
        employment_terms_evidence_digest_sha256,
        capacity_policy_evidence_digest_sha256,
        reviewer_identity_evidence_digest_sha256,
        requester_actor_reference,
        reviewer_actor_reference,
        applied_by_actor_reference,
        reason_code,
        reviewed_at,
        review_recorded_at,
        review_audit_event_reference,
        review_audit_envelope_digest_sha256,
        application_audit_event_reference,
        application_outbox_event_reference,
        application_audit_envelope_digest_sha256,
        prior_capacity_match_state,
        evidence_version
    ) VALUES (
        requested_tenant_id,
        requested_capacity_version_id,
        existing_capacity_record_id,
        current_capacity,
        proposed_capacity,
        requested_effective_on,
        requested_review_evidence_json,
        requested_review_evidence_digest_sha256,
        review_payload->>'employment_terms_evidence_digest',
        review_payload->>'capacity_policy_evidence_digest',
        review_payload->>'reviewer_identity_evidence_digest',
        review_payload->>'requester_actor_reference',
        review_payload->>'reviewer_actor_reference',
        requested_applied_by_actor_reference,
        review_payload->>'reason_code',
        (review_payload->>'reviewed_at')::timestamptz,
        (review_payload->>'recorded_at')::timestamptz,
        requested_review_audit_event_reference,
        requested_review_audit_envelope_digest_sha256,
        requested_application_audit_event_reference,
        requested_application_outbox_event_reference,
        requested_application_audit_envelope_digest_sha256,
        'bootstrap_from_reviewed_terms',
        1
    );

    RETURN requested_capacity_version_id;
END;
$$;

COMMENT ON FUNCTION apply_employment_work_capacity_change(uuid, uuid, uuid, uuid, text, text, text, text, text, text, text, text) IS
    'Applies one human-reviewed Employment capacity change after tenant-context, evidence, actor-separation, Employment-state, and prior-authoritative-capacity validation. The production host must resolve purpose-bound authority and immutable audit/outbox contracts before invocation.';

REVOKE ALL ON FUNCTION apply_employment_work_capacity_change(uuid, uuid, uuid, uuid, text, text, text, text, text, text, text, text) FROM PUBLIC;

CREATE FUNCTION protect_employment_work_capacity_anchor_immutability()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Employment work-capacity identity is immutable'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION protect_employment_work_capacity_anchor_immutability() IS
    'Rejects UPDATE and DELETE on the stable Employment work-capacity anchor.';

CREATE TRIGGER employment_work_capacity_anchor_immutability_guard
BEFORE UPDATE OR DELETE ON employment_work_capacity_record
FOR EACH ROW
EXECUTE FUNCTION protect_employment_work_capacity_anchor_immutability();

CREATE FUNCTION protect_employment_work_capacity_version_history()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Employment work-capacity history is immutable'
            USING ERRCODE = '55000';
    END IF;

    IF OLD.recorded_to IS NULL
       AND NEW.recorded_to IS NOT NULL
       AND NEW.recorded_to IS NOT DISTINCT FROM pg_catalog.transaction_timestamp()
       AND (pg_catalog.to_jsonb(NEW) - 'recorded_to') =
           (pg_catalog.to_jsonb(OLD) - 'recorded_to') THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION 'Employment work-capacity history is immutable except for database-time correction closure'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION protect_employment_work_capacity_version_history() IS
    'Allows only closing an open system-recorded interval at current transaction time; all business/evidence changes append new versions.';

CREATE TRIGGER employment_work_capacity_version_history_guard
BEFORE UPDATE OR DELETE ON employment_work_capacity_version
FOR EACH ROW
EXECUTE FUNCTION protect_employment_work_capacity_version_history();

CREATE FUNCTION reject_employment_work_capacity_truncate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Employment work-capacity history cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION reject_employment_work_capacity_truncate() IS
    'Rejects TRUNCATE so capacity history cannot bypass row-level immutability.';

CREATE TRIGGER employment_work_capacity_record_truncate_guard
BEFORE TRUNCATE ON employment_work_capacity_record
FOR EACH STATEMENT
EXECUTE FUNCTION reject_employment_work_capacity_truncate();

CREATE TRIGGER employment_work_capacity_version_truncate_guard
BEFORE TRUNCATE ON employment_work_capacity_version
FOR EACH STATEMENT
EXECUTE FUNCTION reject_employment_work_capacity_truncate();

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON employment_work_capacity_record FROM PUBLIC;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON employment_work_capacity_version FROM PUBLIC;

ALTER TABLE employment_work_capacity_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE employment_work_capacity_record FORCE ROW LEVEL SECURITY;
ALTER TABLE employment_work_capacity_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE employment_work_capacity_version FORCE ROW LEVEL SECURITY;

CREATE POLICY employment_work_capacity_record_tenant_isolation_policy
ON employment_work_capacity_record
USING (
    tenant_record_id = NULLIF(
        pg_catalog.current_setting('orgmetra.tenant_record_id', true),
        ''
    )::uuid
)
WITH CHECK (
    tenant_record_id = NULLIF(
        pg_catalog.current_setting('orgmetra.tenant_record_id', true),
        ''
    )::uuid
);

CREATE POLICY employment_work_capacity_version_tenant_isolation_policy
ON employment_work_capacity_version
USING (
    tenant_record_id = NULLIF(
        pg_catalog.current_setting('orgmetra.tenant_record_id', true),
        ''
    )::uuid
)
WITH CHECK (
    tenant_record_id = NULLIF(
        pg_catalog.current_setting('orgmetra.tenant_record_id', true),
        ''
    )::uuid
);
