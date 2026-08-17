-- Bind performance criterion observations to the worker's actual job context.
--
-- criterion_observation is downstream evidence for performance management and
-- criterion-related validity. A same-tenant foreign key alone cannot prove that
-- the selected criterion belongs to a job the observed worker actually held at
-- the business-time coordinate being measured. This trigger closes that gap
-- without turning an observation into an automated employment decision.

CREATE FUNCTION enforce_criterion_observation_scope()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
    observation_effective_date date;
    criterion_job_profile_id uuid;
BEGIN
    -- Effective periods in the current foundation are date-granular. Convert
    -- the evidence instant through UTC explicitly so session TimeZone cannot
    -- move an observation across a date boundary and bypass temporal checks.
    observation_effective_date := (NEW.observed_at AT TIME ZONE 'UTC')::date;

    SELECT blueprint.job_profile_id
    INTO criterion_job_profile_id
    FROM criterion_blueprint AS blueprint
    WHERE blueprint.tenant_record_id = NEW.tenant_record_id
      AND blueprint.criterion_blueprint_id = NEW.criterion_blueprint_id
      AND blueprint.effective_from <= observation_effective_date
      AND (
          blueprint.effective_to IS NULL
          OR observation_effective_date < blueprint.effective_to
      )
      AND blueprint.recorded_from <= statement_timestamp()
      AND (
          blueprint.recorded_to IS NULL
          OR statement_timestamp() < blueprint.recorded_to
      );

    IF criterion_job_profile_id IS NULL THEN
        RAISE EXCEPTION 'criterion observation references a criterion outside its effective or current-recorded period'
            USING ERRCODE = '23514';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM performance_cycle AS cycle_record
        WHERE cycle_record.tenant_record_id = NEW.tenant_record_id
          AND cycle_record.performance_cycle_id = NEW.performance_cycle_id
          AND cycle_record.effective_from <= observation_effective_date
          AND (
              cycle_record.effective_to IS NULL
              OR observation_effective_date < cycle_record.effective_to
          )
          AND cycle_record.recorded_from <= statement_timestamp()
          AND (
              cycle_record.recorded_to IS NULL
              OR statement_timestamp() < cycle_record.recorded_to
          )
    ) THEN
        RAISE EXCEPTION 'criterion observation is outside the performance cycle effective period'
            USING ERRCODE = '23514';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM assignment_record AS assignment
        JOIN position_record AS position
          ON position.tenant_record_id = assignment.tenant_record_id
         AND position.position_record_id = assignment.position_record_id
        WHERE assignment.tenant_record_id = NEW.tenant_record_id
          AND assignment.person_record_id = NEW.person_record_id
          AND position.job_profile_id = criterion_job_profile_id
          AND assignment.effective_from <= observation_effective_date
          AND (
              assignment.effective_to IS NULL
              OR observation_effective_date < assignment.effective_to
          )
          AND assignment.recorded_from <= statement_timestamp()
          AND (
              assignment.recorded_to IS NULL
              OR statement_timestamp() < assignment.recorded_to
          )
          AND position.recorded_from <= statement_timestamp()
          AND (
              position.recorded_to IS NULL
              OR statement_timestamp() < position.recorded_to
          )
    ) THEN
        RAISE EXCEPTION 'criterion observation does not match an effective worker assignment for the criterion job'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER criterion_observation_scope_guard
BEFORE INSERT ON criterion_observation
FOR EACH ROW
EXECUTE FUNCTION enforce_criterion_observation_scope();
