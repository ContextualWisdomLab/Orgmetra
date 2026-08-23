-- Normalize base compensation to Employment so concurrent employments retain
-- independent compensation truth. The legacy person-scoped relation remains
-- readable for historical compatibility but no longer accepts new writes.

CREATE TABLE employment_base_compensation_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    employment_base_compensation_record_id uuid PRIMARY KEY,
    employment_record_id uuid NOT NULL,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    recorded_to timestamptz,
    CONSTRAINT employment_base_compensation_employment_tenant_fk
        FOREIGN KEY (tenant_record_id, employment_record_id)
        REFERENCES employment_record(tenant_record_id, employment_record_id),
    CONSTRAINT employment_base_compensation_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT employment_base_compensation_tenant_identity_unique
        UNIQUE (tenant_record_id, employment_base_compensation_record_id),
    CONSTRAINT employment_base_compensation_employment_unique
        UNIQUE (tenant_record_id, employment_record_id)
);

CREATE TABLE employment_base_compensation_version (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    employment_base_compensation_version_id uuid PRIMARY KEY,
    employment_base_compensation_record_id uuid NOT NULL,
    base_compensation_amount numeric(19,4) NOT NULL,
    currency_code text NOT NULL,
    pay_rate_period_code text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT pg_catalog.transaction_timestamp(),
    recorded_to timestamptz,
    CONSTRAINT employment_base_compensation_version_tenant_fk
        FOREIGN KEY (tenant_record_id, employment_base_compensation_record_id)
        REFERENCES employment_base_compensation_record(
            tenant_record_id,
            employment_base_compensation_record_id
        ),
    CONSTRAINT employment_base_compensation_amount_check
        CHECK (base_compensation_amount >= 0),
    CONSTRAINT employment_base_compensation_currency_check
        CHECK (currency_code ~ '^[A-Z]{3}$'),
    CONSTRAINT employment_base_compensation_rate_period_check
        CHECK (
            pay_rate_period_code IN (
                'hour',
                'day',
                'week',
                'biweekly',
                'semimonthly',
                'month',
                'year'
            )
        ),
    CONSTRAINT employment_base_compensation_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT employment_base_compensation_version_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT employment_base_compensation_version_tenant_identity_unique
        UNIQUE (tenant_record_id, employment_base_compensation_version_id),
    CONSTRAINT employment_base_compensation_bitemporal_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            employment_base_compensation_record_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE FUNCTION enforce_employment_base_compensation_recorded_from()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.recorded_to IS NOT NULL THEN
        RAISE EXCEPTION 'base-compensation recorded_to must be NULL on insert'
            USING ERRCODE = '22023';
    END IF;
    IF NEW.recorded_from IS DISTINCT FROM pg_catalog.transaction_timestamp() THEN
        RAISE EXCEPTION 'base-compensation recorded_from must equal the current transaction timestamp'
            USING ERRCODE = '22023';
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION enforce_employment_base_compensation_recorded_from() IS
    'Guards new base-compensation anchors and versions: rejects caller-preclosed evidence and requires recorded_from to equal the current PostgreSQL transaction timestamp.';

CREATE TRIGGER employment_base_compensation_record_system_time_guard
BEFORE INSERT ON employment_base_compensation_record
FOR EACH ROW
EXECUTE FUNCTION enforce_employment_base_compensation_recorded_from();

CREATE TRIGGER employment_base_compensation_version_system_time_guard
BEFORE INSERT ON employment_base_compensation_version
FOR EACH ROW
EXECUTE FUNCTION enforce_employment_base_compensation_recorded_from();

CREATE FUNCTION enforce_employment_base_compensation_recorded_to()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.recorded_to IS DISTINCT FROM OLD.recorded_to
       AND NEW.recorded_to IS DISTINCT FROM pg_catalog.transaction_timestamp() THEN
        RAISE EXCEPTION 'base-compensation recorded_to must equal the current transaction timestamp'
            USING ERRCODE = '22023';
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION enforce_employment_base_compensation_recorded_to() IS
    'Guards base-compensation history closure: a changed recorded_to is accepted only when it equals the current PostgreSQL transaction timestamp.';

CREATE TRIGGER employment_base_compensation_record_system_time_close_guard
BEFORE UPDATE ON employment_base_compensation_record
FOR EACH ROW
EXECUTE FUNCTION enforce_employment_base_compensation_recorded_to();

CREATE TRIGGER employment_base_compensation_version_system_time_close_guard
BEFORE UPDATE ON employment_base_compensation_version
FOR EACH ROW
EXECUTE FUNCTION enforce_employment_base_compensation_recorded_to();

CREATE TRIGGER employment_base_compensation_record_bitemporal_guard
BEFORE UPDATE OR DELETE ON employment_base_compensation_record
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE TRIGGER employment_base_compensation_version_bitemporal_guard
BEFORE UPDATE OR DELETE ON employment_base_compensation_version
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE FUNCTION reject_legacy_compensation_insert()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'legacy compensation_record is read-only for new writes; use employment_base_compensation_record and employment_base_compensation_version'
        USING ERRCODE = '55000';
END;
$$;

COMMENT ON FUNCTION reject_legacy_compensation_insert() IS
    'Rejects every new Person-scoped legacy compensation_record insert so new base-compensation truth must use the Employment-scoped relations.';

CREATE TRIGGER compensation_record_legacy_insert_guard
BEFORE INSERT ON compensation_record
FOR EACH ROW
EXECUTE FUNCTION reject_legacy_compensation_insert();

ALTER TABLE employment_base_compensation_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE employment_base_compensation_record FORCE ROW LEVEL SECURITY;
CREATE POLICY employment_base_compensation_record_scope_policy
ON employment_base_compensation_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE employment_base_compensation_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE employment_base_compensation_version FORCE ROW LEVEL SECURITY;
CREATE POLICY employment_base_compensation_version_scope_policy
ON employment_base_compensation_version
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

COMMENT ON TABLE employment_base_compensation_record IS
    'Durable tenant-scoped base-compensation anchor owned by one Employment; system-recorded time is database-authored and legacy person-scoped compensation_record is historical-read only.';
COMMENT ON TABLE employment_base_compensation_version IS
    'Single-valued bitemporal base-compensation amount, currency transport code, and pay-rate period for one Employment compensation anchor; system-recorded time is database-authored.';
