-- Seal high-impact decision evidence from database-owned canonical membership.
-- Open evidence sets do not carry a caller-supplied digest. Finalization computes
-- SHA-256 over the sorted versioned evidence members in the same transaction
-- that records the accountable selection decision.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE decision_evidence_set
    ALTER COLUMN evidence_set_digest DROP NOT NULL;

ALTER TABLE decision_evidence_set
    DROP CONSTRAINT decision_evidence_seal_pair_check;

ALTER TABLE decision_evidence_set
    ADD CONSTRAINT decision_evidence_seal_state_check
    CHECK (
        (
            sealed_at IS NULL
            AND sealed_selection_decision_id IS NULL
            AND evidence_set_digest IS NULL
        )
        OR
        (
            sealed_at IS NOT NULL
            AND sealed_selection_decision_id IS NOT NULL
            AND evidence_set_digest IS NOT NULL
        )
    );

CREATE OR REPLACE FUNCTION protect_evidence_set_seal()
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
       OR OLD.evidence_set_digest IS NOT NULL
       OR NEW.sealed_at IS NULL
       OR NEW.sealed_selection_decision_id IS NULL
       OR NEW.evidence_set_digest IS NULL
       OR NEW.digest_algorithm_code <> 'sha256'
       OR to_jsonb(NEW) - 'sealed_at' - 'sealed_selection_decision_id' - 'evidence_set_digest'
          <> to_jsonb(OLD) - 'sealed_at' - 'sealed_selection_decision_id' - 'evidence_set_digest' THEN
        RAISE EXCEPTION 'decision evidence set may only transition once from open to database-sealed'
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION seal_decision_evidence_set()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    locked_evidence_set_id uuid;
    evidence_member_count bigint;
    computed_evidence_digest text;
BEGIN
    -- Serialize finalization with evidence membership writes before taking the
    -- membership snapshot. reject_sealed_evidence_insert() takes the same row
    -- lock, so a member that began first commits before this digest is computed.
    SELECT decision_evidence_set_id
    INTO locked_evidence_set_id
    FROM decision_evidence_set
    WHERE tenant_record_id = NEW.tenant_record_id
      AND decision_evidence_set_id = NEW.decision_evidence_set_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'decision evidence set does not exist in the tenant'
            USING ERRCODE = '23503';
    END IF;

    SELECT
        count(*),
        encode(
            digest(
                jsonb_agg(
                    jsonb_build_array(evidence_reference, evidence_version_code)
                    ORDER BY evidence_reference, evidence_version_code
                )::text,
                'sha256'
            ),
            'hex'
        )
    INTO evidence_member_count, computed_evidence_digest
    FROM selection_decision_evidence
    WHERE tenant_record_id = NEW.tenant_record_id
      AND decision_evidence_set_id = NEW.decision_evidence_set_id;

    IF evidence_member_count = 0 THEN
        RAISE EXCEPTION 'decision evidence set must contain at least one member before finalization'
            USING ERRCODE = '23514';
    END IF;

    UPDATE decision_evidence_set
    SET evidence_set_digest = computed_evidence_digest,
        sealed_at = NEW.recorded_at,
        sealed_selection_decision_id = NEW.selection_decision_id
    WHERE tenant_record_id = NEW.tenant_record_id
      AND decision_evidence_set_id = NEW.decision_evidence_set_id
      AND sealed_selection_decision_id IS NULL
      AND evidence_set_digest IS NULL;

    IF FOUND THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION 'evidence set is already sealed by a decision'
        USING ERRCODE = '55000';
END;
$$;

CREATE FUNCTION validate_evidence_set_decision_binding()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.sealed_selection_decision_id IS NULL THEN
        RETURN NEW;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM selection_decision
        WHERE tenant_record_id = NEW.tenant_record_id
          AND selection_decision_id = NEW.sealed_selection_decision_id
          AND decision_evidence_set_id = NEW.decision_evidence_set_id
    ) THEN
        RAISE EXCEPTION 'sealed evidence set must reference the decision that consumed it'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER decision_evidence_set_binding_guard
AFTER INSERT OR UPDATE OF sealed_selection_decision_id ON decision_evidence_set
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION validate_evidence_set_decision_binding();
