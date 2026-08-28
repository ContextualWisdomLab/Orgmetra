-- Govern candidate-initiated application withdrawal without reusing raw workflow
-- stage codes for a terminal action. The application layer remains responsible
-- for authenticating the candidate; this persistence boundary requires the
-- resulting identity-resolution evidence, candidate actor, withdrawal evidence,
-- and exact immutable audit/outbox correlation to agree before accepting a row.

BEGIN;

SET LOCAL search_path = public, pg_catalog;

CREATE TABLE candidate_withdrawal_record (
    tenant_record_id uuid NOT NULL REFERENCES public.tenant_record(tenant_record_id),
    candidate_withdrawal_record_id uuid PRIMARY KEY,
    candidate_application_record_id uuid NOT NULL,
    initiating_actor_reference text NOT NULL,
    identity_resolution_reference text NOT NULL,
    identity_resolution_digest text NOT NULL,
    withdrawal_evidence_reference text NOT NULL,
    withdrawal_evidence_digest text NOT NULL,
    evidence_version integer NOT NULL,
    withdrawn_at timestamptz NOT NULL,
    audit_event_record_id uuid NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    CONSTRAINT candidate_withdrawal_record_id_operational_check
        CHECK (
            candidate_withdrawal_record_id <> '00000000-0000-0000-0000-000000000000'::uuid
            AND candidate_withdrawal_record_id <> 'ffffffff-ffff-ffff-ffff-ffffffffffff'::uuid
        ),
    CONSTRAINT candidate_withdrawal_application_tenant_fk
        FOREIGN KEY (tenant_record_id, candidate_application_record_id)
        REFERENCES public.candidate_application_record(
            tenant_record_id, candidate_application_record_id
        ),
    CONSTRAINT candidate_withdrawal_audit_tenant_fk
        FOREIGN KEY (tenant_record_id, audit_event_record_id)
        REFERENCES public.audit_event_record(tenant_record_id, audit_event_record_id),
    CONSTRAINT candidate_withdrawal_actor_reference_check
        CHECK (
            initiating_actor_reference ~
                '^candidate:[A-Za-z0-9][A-Za-z0-9._~-]*$'
        ),
    CONSTRAINT candidate_withdrawal_identity_reference_check
        CHECK (
            identity_resolution_reference ~
                '^identity_resolution:[A-Za-z0-9][A-Za-z0-9._~-]*$'
        ),
    CONSTRAINT candidate_withdrawal_identity_digest_check
        CHECK (identity_resolution_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT candidate_withdrawal_evidence_reference_check
        CHECK (
            withdrawal_evidence_reference ~
                '^candidate_withdrawal_evidence:[A-Za-z0-9][A-Za-z0-9._~-]*$'
        ),
    CONSTRAINT candidate_withdrawal_evidence_digest_check
        CHECK (withdrawal_evidence_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT candidate_withdrawal_evidence_version_check
        CHECK (evidence_version >= 1 AND evidence_version <= 1000000),
    CONSTRAINT candidate_withdrawal_recorded_order_check
        CHECK (withdrawn_at <= recorded_at),
    CONSTRAINT candidate_withdrawal_tenant_identity_unique
        UNIQUE (tenant_record_id, candidate_withdrawal_record_id),
    CONSTRAINT candidate_withdrawal_application_unique
        UNIQUE (tenant_record_id, candidate_application_record_id),
    CONSTRAINT candidate_withdrawal_audit_identity_unique
        UNIQUE (tenant_record_id, audit_event_record_id)
);

CREATE FUNCTION public.validate_candidate_withdrawal_evidence()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    application_submitted_at timestamptz;
    audit_event_envelope jsonb;
    audit_event_time timestamptz;
BEGIN
    SELECT application_record.submitted_at
    INTO application_submitted_at
    FROM public.candidate_application_record AS application_record
    WHERE application_record.tenant_record_id = NEW.tenant_record_id
      AND application_record.candidate_application_record_id =
          NEW.candidate_application_record_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'candidate withdrawal requires a tenant-local application'
            USING ERRCODE = '23503';
    END IF;

    IF NEW.withdrawn_at < application_submitted_at THEN
        RAISE EXCEPTION 'candidate withdrawal cannot predate application submission'
            USING ERRCODE = '23514';
    END IF;

    SELECT audit_record.canonical_event_json::jsonb
    INTO audit_event_envelope
    FROM public.audit_event_record AS audit_record
    WHERE audit_record.tenant_record_id = NEW.tenant_record_id
      AND audit_record.audit_event_record_id = NEW.audit_event_record_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'candidate withdrawal requires a tenant-local immutable audit event'
            USING ERRCODE = '23503';
    END IF;

    audit_event_time := (audit_event_envelope ->> 'time')::timestamptz;

    IF audit_event_envelope ->> 'source' <> 'urn:orgmetra:talent_acquisition'
       OR audit_event_envelope ->> 'type' <> 'orgmetra.candidate.application_withdrawn'
       OR audit_event_envelope ->> 'subject'
          <> 'candidate_withdrawal_record:' || NEW.candidate_withdrawal_record_id::text
       OR audit_event_envelope ->> 'orgmetraactor' <> NEW.initiating_actor_reference
       OR audit_event_envelope ->> 'orgmetrapurpose' <> 'candidate_withdrawal'
       OR audit_event_envelope ->> 'orgmetrareason' <> 'candidate_requested'
       OR audit_event_envelope ->> 'orgmetraevidence' <> NEW.withdrawal_evidence_reference
       OR audit_event_envelope #>> '{data,identity_resolution_reference}'
          <> NEW.identity_resolution_reference
       OR audit_event_envelope #>> '{data,identity_resolution_digest}'
          <> NEW.identity_resolution_digest
       OR audit_event_envelope #>> '{data,withdrawal_evidence_digest}'
          <> NEW.withdrawal_evidence_digest
       OR audit_event_envelope #>> '{data,evidence_version}'
          <> NEW.evidence_version::text
       OR audit_event_envelope ? 'orgmetraconfirmation'
       OR (audit_event_envelope #>> '{data,high_impact}')::boolean IS NOT FALSE
       OR audit_event_envelope #>> '{data,result_code}' <> 'application_withdrawn'
       OR audit_event_time <> NEW.withdrawn_at
       OR audit_event_time > NEW.recorded_at THEN
        RAISE EXCEPTION 'candidate withdrawal audit envelope does not bind exact candidate provenance'
            USING ERRCODE = '23514';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM public.outbox_delivery_record AS delivery_record
        WHERE delivery_record.tenant_record_id = NEW.tenant_record_id
          AND delivery_record.audit_event_record_id = NEW.audit_event_record_id
    ) THEN
        RAISE EXCEPTION 'candidate withdrawal audit event requires transactional outbox delivery evidence'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER candidate_withdrawal_governance_guard
BEFORE INSERT ON candidate_withdrawal_record
FOR EACH ROW
EXECUTE FUNCTION public.validate_candidate_withdrawal_evidence();

CREATE FUNCTION public.reject_candidate_withdrawal_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'candidate withdrawal evidence is append-only'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER candidate_withdrawal_append_only_guard
BEFORE UPDATE OR DELETE ON candidate_withdrawal_record
FOR EACH ROW
EXECUTE FUNCTION public.reject_candidate_withdrawal_mutation();

CREATE FUNCTION public.reject_candidate_withdrawal_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'candidate withdrawal evidence cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER candidate_withdrawal_truncate_guard
BEFORE TRUNCATE ON candidate_withdrawal_record
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_candidate_withdrawal_truncate();

REVOKE TRUNCATE ON candidate_withdrawal_record FROM PUBLIC;

ALTER TABLE candidate_withdrawal_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_withdrawal_record FORCE ROW LEVEL SECURITY;
CREATE POLICY candidate_withdrawal_scope_policy ON public.candidate_withdrawal_record
USING (tenant_record_id = public.current_tenant_record_id())
WITH CHECK (tenant_record_id = public.current_tenant_record_id());

COMMIT;
