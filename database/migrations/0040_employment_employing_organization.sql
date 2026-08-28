-- Employment employing-organization truth.
--
-- An Employment and a Position answer different questions. A Position belongs
-- to an organizational seat; this relation records which legal organization
-- employs the worker for the Employment itself. It is intentionally separate
-- from Position/Assignment so a legal-employer change is not inferred from a
-- seat move and a seat move is not inferred from a legal-employer change.

CREATE TABLE employment_employing_organization_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    employment_employing_organization_record_id uuid PRIMARY KEY,
    employment_record_id uuid NOT NULL,
    employing_organization_unit_id uuid NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_from timestamptz NOT NULL DEFAULT now(),
    recorded_to timestamptz,
    CONSTRAINT employment_employing_organization_employment_tenant_fk
        FOREIGN KEY (tenant_record_id, employment_record_id)
        REFERENCES employment_record(tenant_record_id, employment_record_id),
    CONSTRAINT employment_employing_organization_unit_tenant_fk
        FOREIGN KEY (tenant_record_id, employing_organization_unit_id)
        REFERENCES organization_unit(tenant_record_id, organization_unit_id),
    CONSTRAINT employment_employing_organization_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT employment_employing_organization_recorded_period_check
        CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CONSTRAINT employment_employing_organization_tenant_operational_uuid_check
        CHECK (is_operational_uuid(tenant_record_id)),
    CONSTRAINT employment_employing_organization_record_operational_uuid_check
        CHECK (is_operational_uuid(employment_employing_organization_record_id)),
    CONSTRAINT employment_employing_organization_employment_uuid_check
        CHECK (is_operational_uuid(employment_record_id)),
    CONSTRAINT employment_employing_organization_unit_operational_uuid_check
        CHECK (is_operational_uuid(employing_organization_unit_id)),
    CONSTRAINT employment_employing_organization_tenant_identity_unique
        UNIQUE (tenant_record_id, employment_employing_organization_record_id),
    CONSTRAINT employment_employing_organization_bitemporal_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            employment_record_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&,
            tstzrange(recorded_from, recorded_to, '[)') WITH &&
        )
);

CREATE INDEX employment_employing_organization_unit_lookup_index
ON employment_employing_organization_record (
    tenant_record_id,
    employing_organization_unit_id
);

CREATE FUNCTION validate_employment_employing_organization_scope()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    requested_effective_range daterange;
    legal_entity_coverage datemultirange;
    employment_coverage datemultirange;
BEGIN
    requested_effective_range := daterange(NEW.effective_from, NEW.effective_to, '[)');

    -- Missing/cross-tenant organization anchors are left to the tenant-qualified
    -- foreign key so callers receive the structural integrity failure rather
    -- than a misleading classification error.
    IF NOT EXISTS (
        SELECT 1
        FROM organization_unit
        WHERE tenant_record_id = NEW.tenant_record_id
          AND organization_unit_id = NEW.employing_organization_unit_id
    ) THEN
        RETURN NEW;
    END IF;

    SELECT range_agg(daterange(effective_from, effective_to, '[)'))
    INTO legal_entity_coverage
    FROM organization_unit_version
    WHERE tenant_record_id = NEW.tenant_record_id
      AND organization_unit_id = NEW.employing_organization_unit_id
      AND organization_type_code = 'legal_entity'
      AND tstzrange(recorded_from, recorded_to, '[)') @> NEW.recorded_from;

    IF legal_entity_coverage IS NULL
       OR NOT (legal_entity_coverage @> requested_effective_range) THEN
        RAISE EXCEPTION 'employing organization must be a legal_entity over the full effective interval at the recorded-time coordinate'
            USING ERRCODE = '23514';
    END IF;

    SELECT range_agg(daterange(effective_from, effective_to, '[)'))
    INTO employment_coverage
    FROM employment_record_version
    WHERE tenant_record_id = NEW.tenant_record_id
      AND employment_record_id = NEW.employment_record_id
      AND employment_status_code IN ('active', 'leave')
      AND tstzrange(recorded_from, recorded_to, '[)') @> NEW.recorded_from;

    IF employment_coverage IS NULL
       OR NOT (employment_coverage @> requested_effective_range) THEN
        RAISE EXCEPTION 'employing organization interval must be covered by active or leave Employment truth at the recorded-time coordinate'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER employment_employing_organization_scope_guard
BEFORE INSERT ON employment_employing_organization_record
FOR EACH ROW
EXECUTE FUNCTION validate_employment_employing_organization_scope();

CREATE FUNCTION employment_employing_organization_exact_one_is_valid(
    target_tenant_record_id uuid,
    target_employment_record_id uuid
)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
WITH active_employment_versions AS (
    SELECT effective_from, effective_to, recorded_from, recorded_to
    FROM employment_record_version
    WHERE tenant_record_id = target_tenant_record_id
      AND employment_record_id = target_employment_record_id
      AND employment_status_code IN ('active', 'leave')
), relationship_rows AS (
    SELECT effective_from, effective_to, recorded_from, recorded_to,
           employing_organization_unit_id
    FROM employment_employing_organization_record
    WHERE tenant_record_id = target_tenant_record_id
      AND employment_record_id = target_employment_record_id
), recorded_points AS (
    SELECT recorded_from AS recorded_point FROM active_employment_versions
    UNION
    SELECT recorded_to FROM active_employment_versions WHERE recorded_to IS NOT NULL
    UNION
    SELECT recorded_from FROM relationship_rows
    UNION
    SELECT recorded_to FROM relationship_rows WHERE recorded_to IS NOT NULL
    UNION
    SELECT organization_version.recorded_from
    FROM organization_unit_version organization_version
    WHERE organization_version.tenant_record_id = target_tenant_record_id
      AND organization_version.organization_unit_id IN (
          SELECT employing_organization_unit_id FROM relationship_rows
      )
    UNION
    SELECT organization_version.recorded_to
    FROM organization_unit_version organization_version
    WHERE organization_version.tenant_record_id = target_tenant_record_id
      AND organization_version.organization_unit_id IN (
          SELECT employing_organization_unit_id FROM relationship_rows
      )
      AND organization_version.recorded_to IS NOT NULL
)
SELECT NOT EXISTS (
    SELECT 1
    FROM active_employment_versions employment_version
    JOIN recorded_points point
      ON tstzrange(
             employment_version.recorded_from,
             employment_version.recorded_to,
             '[)'
         ) @> point.recorded_point
    WHERE NOT EXISTS (
        SELECT 1
        FROM (
            SELECT range_agg(
                       daterange(
                           relationship.effective_from,
                           relationship.effective_to,
                           '[)'
                       )
                   ) AS covered_effective_period
            FROM relationship_rows relationship
            WHERE tstzrange(
                      relationship.recorded_from,
                      relationship.recorded_to,
                      '[)'
                  ) @> point.recorded_point
              AND EXISTS (
                  SELECT 1
                  FROM (
                      SELECT range_agg(
                                 daterange(
                                     organization_version.effective_from,
                                     organization_version.effective_to,
                                     '[)'
                                 )
                             ) AS legal_entity_effective_period
                      FROM organization_unit_version organization_version
                      WHERE organization_version.tenant_record_id = target_tenant_record_id
                        AND organization_version.organization_unit_id = relationship.employing_organization_unit_id
                        AND organization_version.organization_type_code = 'legal_entity'
                        AND tstzrange(
                                organization_version.recorded_from,
                                organization_version.recorded_to,
                                '[)'
                            ) @> point.recorded_point
                  ) legal_entity
                  WHERE legal_entity.legal_entity_effective_period @> daterange(
                      relationship.effective_from,
                      relationship.effective_to,
                      '[)'
                  )
              )
        ) relationship_coverage
        WHERE relationship_coverage.covered_effective_period @> daterange(
            employment_version.effective_from,
            employment_version.effective_to,
            '[)'
        )
    )
);
$$;

CREATE FUNCTION enforce_employment_employing_organization_exact_one()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_tenant_record_id uuid;
    v_employment_record_id uuid;
    v_organization_unit_id uuid;
    old_tenant_record_id uuid;
    old_organization_unit_id uuid;
    affected_tenant_record_id uuid;
    affected_employment_record_id uuid;
BEGIN
    IF TG_TABLE_NAME IN (
        'employment_record_version',
        'employment_employing_organization_record'
    ) THEN
        IF TG_OP = 'DELETE' THEN
            v_tenant_record_id := OLD.tenant_record_id;
            v_employment_record_id := OLD.employment_record_id;
        ELSE
            v_tenant_record_id := NEW.tenant_record_id;
            v_employment_record_id := NEW.employment_record_id;
        END IF;

        IF NOT employment_employing_organization_exact_one_is_valid(
            v_tenant_record_id,
            v_employment_record_id
        ) THEN
            RAISE EXCEPTION 'active or leave Employment must have exactly one legal employer across every effective and recorded-time coordinate'
                USING ERRCODE = '23514';
        END IF;

        IF TG_OP = 'UPDATE'
           AND (
               OLD.tenant_record_id IS DISTINCT FROM NEW.tenant_record_id
               OR OLD.employment_record_id IS DISTINCT FROM NEW.employment_record_id
           )
           AND NOT employment_employing_organization_exact_one_is_valid(
               OLD.tenant_record_id,
               OLD.employment_record_id
           ) THEN
            RAISE EXCEPTION 'active or leave Employment must have exactly one legal employer across every effective and recorded-time coordinate'
                USING ERRCODE = '23514';
        END IF;
    ELSE
        IF TG_OP = 'DELETE' THEN
            v_tenant_record_id := OLD.tenant_record_id;
            v_organization_unit_id := OLD.organization_unit_id;
        ELSE
            v_tenant_record_id := NEW.tenant_record_id;
            v_organization_unit_id := NEW.organization_unit_id;
        END IF;

        IF TG_OP = 'UPDATE' THEN
            old_tenant_record_id := OLD.tenant_record_id;
            old_organization_unit_id := OLD.organization_unit_id;
        END IF;

        FOR affected_tenant_record_id, affected_employment_record_id IN
            SELECT DISTINCT relation.tenant_record_id, relation.employment_record_id
            FROM employment_employing_organization_record relation
            WHERE (
                relation.tenant_record_id = v_tenant_record_id
                AND relation.employing_organization_unit_id = v_organization_unit_id
            )
            OR (
                TG_OP = 'UPDATE'
                AND relation.tenant_record_id = old_tenant_record_id
                AND relation.employing_organization_unit_id = old_organization_unit_id
            )
        LOOP
            IF NOT employment_employing_organization_exact_one_is_valid(
                affected_tenant_record_id,
                affected_employment_record_id
            ) THEN
                RAISE EXCEPTION 'active or leave Employment must have exactly one legal employer across every effective and recorded-time coordinate'
                    USING ERRCODE = '23514';
            END IF;
        END LOOP;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER employment_employing_organization_exact_one_employment_guard
AFTER INSERT OR UPDATE OR DELETE ON employment_record_version
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION enforce_employment_employing_organization_exact_one();

CREATE CONSTRAINT TRIGGER employment_employing_organization_exact_one_relationship_guard
AFTER INSERT OR UPDATE OR DELETE ON employment_employing_organization_record
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION enforce_employment_employing_organization_exact_one();

CREATE CONSTRAINT TRIGGER employment_employing_organization_exact_one_organization_guard
AFTER INSERT OR UPDATE OR DELETE ON organization_unit_version
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION enforce_employment_employing_organization_exact_one();

CREATE TRIGGER employment_employing_organization_bitemporal_guard
BEFORE UPDATE OR DELETE ON employment_employing_organization_record
FOR EACH ROW
EXECUTE FUNCTION protect_bitemporal_history();

CREATE FUNCTION reject_employment_employing_organization_truncate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'employment employing-organization history cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER employment_employing_organization_truncate_guard
BEFORE TRUNCATE ON employment_employing_organization_record
FOR EACH STATEMENT
EXECUTE FUNCTION reject_employment_employing_organization_truncate();

ALTER TABLE employment_employing_organization_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE employment_employing_organization_record FORCE ROW LEVEL SECURITY;
CREATE POLICY employment_employing_organization_scope_policy
ON employment_employing_organization_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

REVOKE ALL ON FUNCTION validate_employment_employing_organization_scope() FROM PUBLIC;
REVOKE ALL ON FUNCTION reject_employment_employing_organization_truncate() FROM PUBLIC;

COMMENT ON TABLE employment_employing_organization_record IS
    'Bitemporal tenant-scoped legal-employer relationship for one Employment; distinct from Position and Assignment and corrected by closing recorded time rather than rewriting history.';
COMMENT ON COLUMN employment_employing_organization_record.employing_organization_unit_id IS
    'Organization unit that is legal_entity throughout this effective interval at the row recorded-time coordinate.';
