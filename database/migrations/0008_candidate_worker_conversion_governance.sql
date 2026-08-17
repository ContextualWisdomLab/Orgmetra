-- Govern candidate-to-worker conversion as a tenant-scoped bitemporal fact.
--
-- The original candidate_worker_link is intentionally retained for historical
-- compatibility, but new writes are closed. New conversions must bind a
-- candidate to the resulting person and employment through a sealed,
-- human-confirmed hire decision while preserving effective and recorded time.

CREATE FUNCTION reject_legacy_candidate_worker_link_insert()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'candidate_worker_link is legacy-only; use candidate_worker_conversion_record'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER candidate_worker_link_legacy_insert_guard
BEFORE INSERT ON candidate_worker_link
FOR EACH ROW
EXECUTE FUNCTION reject_legacy_candidate_worker_link_insert();

CREATE TABLE candidate_worker_conversion_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    candidate_worker_conversion_record_id uuid PRIMARY KEY,
    candidate_profile_id uuid NOT NULL,
    person_record_id uuid NOT NULL,
    employment_record_id uuid NOT NULL,
    selection_decision_id uuid NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT candidate_conversion_record_id_operational_check
        CHECK (
            candidate_worker_conversion_record_id <> '00000000-0000-0000-0000-000000000000'::uuid
            AND candidate_worker_conversion_record_id <> 'ffffffff-ffff-ffff-ffff-ffffffffffff'::uuid
        ),
    CONSTRAINT candidate_conversion_candidate_tenant_fk
        FOREIGN KEY (tenant_record_id, candidate_profile_id)
        REFERENCES candidate_profile(tenant_record_id, candidate_profile_id),
    CONSTRAINT candidate_conversion_employment_person_tenant_fk
        FOREIGN KEY (tenant_record_id, employment_record_id, person_record_id)
        REFERENCES employment_record(tenant_record_id, employment_record_id, person_record_id),
    CONSTRAINT candidate_conversion_decision_tenant_fk
        FOREIGN KEY (tenant_record_id, selection_decision_id)
        REFERENCES selection_decision(tenant_record_id, selection_decision_id),
    CONSTRAINT candidate_conversion_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT candidate_conversion_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT candidate_conversion_tenant_identity_unique
        UNIQUE (tenant_record_id, candidate_worker_conversion_record_id),
    CONSTRAINT candidate_conversion_bitemporal_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            candidate_profile_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE FUNCTION validate_candidate_worker_conversion()
RETURNS trigger
LANGUAGE plpgsql
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
    FROM selection_decision AS decision
    JOIN decision_evidence_set AS evidence
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

    IF btrim(actor_reference_value) = ''
       OR btrim(purpose_code_value) = ''
       OR btrim(decision_reason_value) = ''
       OR btrim(confirmation_reference_value) = '' THEN
        RAISE EXCEPTION 'candidate conversion requires actor, purpose, reason, and human confirmation provenance'
            USING ERRCODE = '23514';
    END IF;

    IF btrim(evidence_version_value) = ''
       OR evidence_sealed_at IS NULL
       OR evidence_sealed_decision_id IS DISTINCT FROM NEW.selection_decision_id THEN
        RAISE EXCEPTION 'candidate conversion requires the decision evidence set sealed by the hire decision'
            USING ERRCODE = '23514';
    END IF;

    SELECT count(*)
    INTO evidence_member_count
    FROM selection_decision_evidence
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

    RETURN NEW;
END;
$$;

CREATE TRIGGER candidate_conversion_governance_guard
BEFORE INSERT OR UPDATE ON candidate_worker_conversion_record
FOR EACH ROW
EXECUTE FUNCTION validate_candidate_worker_conversion();

CREATE TRIGGER candidate_conversion_bitemporal_guard
BEFORE UPDATE OR DELETE ON candidate_worker_conversion_record
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

ALTER TABLE candidate_worker_conversion_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_worker_conversion_record FORCE ROW LEVEL SECURITY;
CREATE POLICY candidate_conversion_scope_policy ON candidate_worker_conversion_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());
