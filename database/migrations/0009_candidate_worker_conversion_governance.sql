-- Govern candidate-to-worker conversion as a tenant-scoped bitemporal fact.
--
-- The legacy candidate_worker_link table remains readable for historical
-- compatibility, but new writes are closed. New conversions must bind the
-- candidate to the resulting person and employment through a sealed,
-- human-confirmed hire decision and immutable audit/outbox evidence.

BEGIN;

-- The public schema is PostgreSQL infrastructure rather than an Orgmetra-owned
-- database object. Pin migration-time resolution explicitly while keeping
-- application-owned object names descriptive two-or-more-word snake_case.
SET LOCAL search_path = public, pg_catalog;

CREATE FUNCTION public.reject_legacy_candidate_worker_link_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'candidate_worker_link is legacy-only; use candidate_worker_conversion_record'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER candidate_worker_link_legacy_insert_guard
BEFORE INSERT ON candidate_worker_link
FOR EACH ROW
EXECUTE FUNCTION public.reject_legacy_candidate_worker_link_insert();

CREATE TABLE candidate_worker_conversion_record (
    tenant_record_id uuid NOT NULL REFERENCES public.tenant_record(tenant_record_id),
    candidate_worker_conversion_record_id uuid PRIMARY KEY,
    candidate_profile_id uuid NOT NULL,
    person_record_id uuid NOT NULL,
    employment_record_id uuid NOT NULL,
    selection_decision_id uuid NOT NULL,
    audit_event_record_id uuid NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    recorded_to timestamptz,
    CONSTRAINT candidate_conversion_record_id_operational_check
        CHECK (
            candidate_worker_conversion_record_id <> '00000000-0000-0000-0000-000000000000'::uuid
            AND candidate_worker_conversion_record_id <> 'ffffffff-ffff-ffff-ffff-ffffffffffff'::uuid
        ),
    CONSTRAINT candidate_conversion_candidate_tenant_fk
        FOREIGN KEY (tenant_record_id, candidate_profile_id)
        REFERENCES public.candidate_profile(tenant_record_id, candidate_profile_id),
    CONSTRAINT candidate_conversion_employment_person_tenant_fk
        FOREIGN KEY (tenant_record_id, employment_record_id, person_record_id)
        REFERENCES public.employment_record(tenant_record_id, employment_record_id, person_record_id),
    CONSTRAINT candidate_conversion_decision_tenant_fk
        FOREIGN KEY (tenant_record_id, selection_decision_id)
        REFERENCES public.selection_decision(tenant_record_id, selection_decision_id),
    CONSTRAINT candidate_conversion_audit_tenant_fk
        FOREIGN KEY (tenant_record_id, audit_event_record_id)
        REFERENCES public.audit_event_record(tenant_record_id, audit_event_record_id),
    CONSTRAINT candidate_conversion_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT candidate_conversion_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT candidate_conversion_tenant_identity_unique
        UNIQUE (tenant_record_id, candidate_worker_conversion_record_id),
    CONSTRAINT candidate_conversion_audit_identity_unique
        UNIQUE (tenant_record_id, audit_event_record_id),
    CONSTRAINT candidate_conversion_knowledge_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            candidate_profile_id WITH =,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE FUNCTION public.validate_candidate_worker_conversion()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    decision_candidate_id uuid;
    decision_code_value text;
    actor_reference_value text;
    purpose_code_value text;
    decision_reason_value text;
    confirmation_reference_value text;
    decided_at_value timestamptz;
    evidence_set_id uuid;
    evidence_version_value text;
    evidence_sealed_at timestamptz;
    evidence_sealed_decision_id uuid;
    evidence_member_count bigint;
    audit_event_envelope jsonb;
    audit_event_time timestamptz;
    is_correction boolean;
    expected_event_type text;
    expected_reason_code text;
    expected_result_code text;
BEGIN
    SELECT
        decision.candidate_profile_id,
        decision.decision_code,
        decision.actor_reference,
        decision.purpose_code,
        decision.decision_reason,
        decision.confirmation_reference,
        decision.decided_at,
        decision.decision_evidence_set_id,
        evidence.evidence_set_version_code,
        evidence.sealed_at,
        evidence.sealed_selection_decision_id
    INTO
        decision_candidate_id,
        decision_code_value,
        actor_reference_value,
        purpose_code_value,
        decision_reason_value,
        confirmation_reference_value,
        decided_at_value,
        evidence_set_id,
        evidence_version_value,
        evidence_sealed_at,
        evidence_sealed_decision_id
    FROM public.selection_decision AS decision
    JOIN public.decision_evidence_set AS evidence
      ON evidence.tenant_record_id = decision.tenant_record_id
     AND evidence.decision_evidence_set_id = decision.decision_evidence_set_id
    WHERE decision.tenant_record_id = NEW.tenant_record_id
      AND decision.selection_decision_id = NEW.selection_decision_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'candidate conversion requires a tenant-local selection decision and evidence set'
            USING ERRCODE = '23503';
    END IF;

    IF decision_candidate_id <> NEW.candidate_profile_id THEN
        RAISE EXCEPTION 'candidate conversion decision belongs to a different candidate'
            USING ERRCODE = '23514';
    END IF;

    IF decision_code_value <> 'hire' THEN
        RAISE EXCEPTION 'candidate conversion requires a hire selection decision'
            USING ERRCODE = '23514';
    END IF;

    IF pg_catalog.btrim(actor_reference_value) = ''
       OR pg_catalog.btrim(purpose_code_value) = ''
       OR pg_catalog.btrim(decision_reason_value) = ''
       OR pg_catalog.btrim(confirmation_reference_value) = '' THEN
        RAISE EXCEPTION 'candidate conversion requires actor, purpose, reason, and human confirmation provenance'
            USING ERRCODE = '23514';
    END IF;

    IF pg_catalog.btrim(evidence_version_value) = ''
       OR evidence_sealed_at IS NULL
       OR evidence_sealed_decision_id IS DISTINCT FROM NEW.selection_decision_id THEN
        RAISE EXCEPTION 'candidate conversion requires the decision evidence set sealed by the hire decision'
            USING ERRCODE = '23514';
    END IF;

    SELECT pg_catalog.count(*)
    INTO evidence_member_count
    FROM public.selection_decision_evidence
    WHERE tenant_record_id = NEW.tenant_record_id
      AND decision_evidence_set_id = evidence_set_id;

    IF evidence_member_count < 1 THEN
        RAISE EXCEPTION 'candidate conversion requires at least one versioned decision evidence member'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.recorded_from < decided_at_value THEN
        RAISE EXCEPTION 'candidate conversion cannot be recorded before the hire decision'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.effective_from < decided_at_value::date THEN
        RAISE EXCEPTION 'candidate conversion cannot become effective before the hire decision date'
            USING ERRCODE = '23514';
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM public.candidate_worker_conversion_record
        WHERE tenant_record_id = NEW.tenant_record_id
          AND candidate_profile_id = NEW.candidate_profile_id
          AND candidate_worker_conversion_record_id <> NEW.candidate_worker_conversion_record_id
          AND recorded_to IS NOT NULL
    )
    INTO is_correction;

    IF is_correction THEN
        expected_event_type := 'orgmetra.candidate.worker_conversion_corrected';
        expected_reason_code := 'candidate_conversion_corrected';
        expected_result_code := 'worker_conversion_corrected';
    ELSE
        expected_event_type := 'orgmetra.candidate.worker_converted';
        expected_reason_code := 'candidate_hire_confirmed';
        expected_result_code := 'worker_created';
    END IF;

    SELECT canonical_event_json::jsonb
    INTO audit_event_envelope
    FROM public.audit_event_record
    WHERE tenant_record_id = NEW.tenant_record_id
      AND audit_event_record_id = NEW.audit_event_record_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'candidate conversion requires a tenant-local immutable audit event'
            USING ERRCODE = '23503';
    END IF;

    audit_event_time := (audit_event_envelope ->> 'time')::timestamptz;

    IF audit_event_envelope ->> 'type' <> expected_event_type
       OR audit_event_envelope ->> 'subject'
          <> 'candidate_worker_conversion_record:' || NEW.candidate_worker_conversion_record_id::text
       OR audit_event_envelope ->> 'orgmetraactor' <> actor_reference_value
       OR audit_event_envelope ->> 'orgmetrapurpose' <> purpose_code_value
       OR audit_event_envelope ->> 'orgmetrareason' <> expected_reason_code
       OR audit_event_envelope ->> 'orgmetraevidence'
          <> 'decision_evidence_set:' || evidence_set_id::text
       OR audit_event_envelope ->> 'orgmetraconfirmation' <> confirmation_reference_value
       OR (audit_event_envelope #>> '{data,high_impact}')::boolean IS NOT TRUE
       OR audit_event_envelope #>> '{data,result_code}' <> expected_result_code
       OR audit_event_time < decided_at_value
       OR audit_event_time > NEW.recorded_from THEN
        RAISE EXCEPTION 'candidate conversion audit envelope does not bind exact hire provenance'
            USING ERRCODE = '23514';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM public.outbox_delivery_record
        WHERE tenant_record_id = NEW.tenant_record_id
          AND audit_event_record_id = NEW.audit_event_record_id
    ) THEN
        RAISE EXCEPTION 'candidate conversion audit event requires transactional outbox delivery evidence'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER candidate_conversion_governance_guard
BEFORE INSERT OR UPDATE ON candidate_worker_conversion_record
FOR EACH ROW
EXECUTE FUNCTION public.validate_candidate_worker_conversion();

CREATE TRIGGER candidate_conversion_bitemporal_guard
BEFORE UPDATE OR DELETE ON candidate_worker_conversion_record
FOR EACH ROW
EXECUTE FUNCTION public.protect_bitemporal_history();

CREATE FUNCTION public.reject_candidate_worker_conversion_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'candidate worker conversion history cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER candidate_worker_conversion_truncate_guard
BEFORE TRUNCATE ON candidate_worker_conversion_record
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_candidate_worker_conversion_truncate();

REVOKE TRUNCATE ON candidate_worker_conversion_record FROM PUBLIC;

ALTER TABLE candidate_worker_conversion_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_worker_conversion_record FORCE ROW LEVEL SECURITY;
CREATE POLICY candidate_conversion_scope_policy ON candidate_worker_conversion_record
USING (tenant_record_id = public.current_tenant_record_id())
WITH CHECK (tenant_record_id = public.current_tenant_record_id());

COMMIT;
