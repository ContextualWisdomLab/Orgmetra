-- Govern evidence-backed job-analysis cases without promoting external or model
-- output to authoritative HRIS truth. This migration deliberately reserves 0012:
-- active PRs #26 and #28 own migrations 0010 and 0011 respectively.

BEGIN;

CREATE TABLE source_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    source_record_id uuid PRIMARY KEY,
    source_type_code text NOT NULL,
    source_locator text NOT NULL,
    source_title text NOT NULL,
    publisher_name text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT source_record_operational_id_check
        CHECK (is_operational_uuid(source_record_id)),
    CONSTRAINT source_record_type_code_check
        CHECK (
            source_type_code IN (
                'web_authoritative',
                'internal_document',
                'sme_evidence',
                'occupational_database',
                'llm_draft'
            )
        ),
    CONSTRAINT source_record_locator_check
        CHECK (length(source_locator) BETWEEN 1 AND 2048 AND source_locator !~ '[[:cntrl:]]'),
    CONSTRAINT source_record_web_https_check
        CHECK (source_type_code <> 'web_authoritative' OR source_locator COLLATE "C" ~ '^https://'),
    CONSTRAINT source_record_title_check
        CHECK (length(btrim(source_title)) BETWEEN 1 AND 500),
    CONSTRAINT source_record_publisher_check
        CHECK (length(btrim(publisher_name)) BETWEEN 1 AND 300),
    CONSTRAINT source_record_tenant_identity_unique
        UNIQUE (tenant_record_id, source_record_id),
    CONSTRAINT source_record_tenant_locator_unique
        UNIQUE (tenant_record_id, source_type_code, source_locator)
);

CREATE TABLE source_version (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    source_version_id uuid PRIMARY KEY,
    source_record_id uuid NOT NULL,
    source_version_code text NOT NULL,
    source_content_sha256 text NOT NULL,
    captured_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT source_version_operational_id_check
        CHECK (is_operational_uuid(source_version_id)),
    CONSTRAINT source_version_record_tenant_fk
        FOREIGN KEY (tenant_record_id, source_record_id)
        REFERENCES source_record(tenant_record_id, source_record_id),
    CONSTRAINT source_version_code_check
        CHECK (source_version_code COLLATE "C" ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'),
    CONSTRAINT source_version_digest_check
        CHECK (source_content_sha256 COLLATE "C" ~ '^[0-9a-f]{64}$'),
    CONSTRAINT source_version_recorded_after_capture_check
        CHECK (recorded_at >= captured_at),
    CONSTRAINT source_version_tenant_identity_unique
        UNIQUE (tenant_record_id, source_version_id),
    CONSTRAINT source_version_record_version_unique
        UNIQUE (tenant_record_id, source_record_id, source_version_code)
);

CREATE TABLE job_analysis_case (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    job_analysis_case_id uuid PRIMARY KEY,
    job_profile_id uuid NOT NULL,
    analysis_version_code text NOT NULL,
    analysis_method_code text NOT NULL,
    analyst_reference text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT job_analysis_case_operational_id_check
        CHECK (is_operational_uuid(job_analysis_case_id)),
    CONSTRAINT job_analysis_job_profile_tenant_fk
        FOREIGN KEY (tenant_record_id, job_profile_id)
        REFERENCES job_profile(tenant_record_id, job_profile_id),
    CONSTRAINT job_analysis_version_code_check
        CHECK (analysis_version_code COLLATE "C" ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'),
    CONSTRAINT job_analysis_method_code_check
        CHECK (analysis_method_code COLLATE "C" ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'),
    CONSTRAINT job_analysis_analyst_reference_check
        CHECK (analyst_reference COLLATE "C" ~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$'),
    CONSTRAINT job_analysis_effective_period_check
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT job_analysis_case_tenant_identity_unique
        UNIQUE (tenant_record_id, job_analysis_case_id),
    CONSTRAINT job_analysis_case_job_version_unique
        UNIQUE (tenant_record_id, job_profile_id, analysis_version_code)
);

CREATE TABLE job_analysis_source_link (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    job_analysis_source_link_id uuid PRIMARY KEY,
    job_analysis_case_id uuid NOT NULL,
    source_version_id uuid NOT NULL,
    evidence_role_code text NOT NULL,
    source_span_reference text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT job_analysis_source_link_operational_id_check
        CHECK (is_operational_uuid(job_analysis_source_link_id)),
    CONSTRAINT job_analysis_source_case_tenant_fk
        FOREIGN KEY (tenant_record_id, job_analysis_case_id)
        REFERENCES job_analysis_case(tenant_record_id, job_analysis_case_id),
    CONSTRAINT job_analysis_source_version_tenant_fk
        FOREIGN KEY (tenant_record_id, source_version_id)
        REFERENCES source_version(tenant_record_id, source_version_id),
    CONSTRAINT job_analysis_source_role_code_check
        CHECK (evidence_role_code COLLATE "C" ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'),
    CONSTRAINT job_analysis_source_span_check
        CHECK (length(btrim(source_span_reference)) BETWEEN 1 AND 500),
    CONSTRAINT job_analysis_source_link_tenant_identity_unique
        UNIQUE (tenant_record_id, job_analysis_source_link_id),
    CONSTRAINT job_analysis_source_membership_unique
        UNIQUE (
            tenant_record_id,
            job_analysis_case_id,
            source_version_id,
            evidence_role_code,
            source_span_reference
        )
);

CREATE TABLE task_statement (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    task_statement_id uuid PRIMARY KEY,
    job_analysis_case_id uuid NOT NULL,
    task_sequence_number integer NOT NULL,
    task_text text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT task_statement_operational_id_check
        CHECK (is_operational_uuid(task_statement_id)),
    CONSTRAINT task_statement_case_tenant_fk
        FOREIGN KEY (tenant_record_id, job_analysis_case_id)
        REFERENCES job_analysis_case(tenant_record_id, job_analysis_case_id),
    CONSTRAINT task_statement_sequence_check
        CHECK (task_sequence_number > 0),
    CONSTRAINT task_statement_text_check
        CHECK (length(btrim(task_text)) BETWEEN 10 AND 4000),
    CONSTRAINT task_statement_tenant_identity_unique
        UNIQUE (tenant_record_id, task_statement_id),
    CONSTRAINT task_statement_case_sequence_unique
        UNIQUE (tenant_record_id, job_analysis_case_id, task_sequence_number)
);

CREATE TABLE task_rating (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    task_rating_id uuid PRIMARY KEY,
    task_statement_id uuid NOT NULL,
    rating_dimension_code text NOT NULL,
    rating_value numeric(10,4) NOT NULL,
    scale_minimum_value numeric(10,4) NOT NULL,
    scale_maximum_value numeric(10,4) NOT NULL,
    rater_group_code text NOT NULL,
    sample_size_count integer NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT task_rating_operational_id_check
        CHECK (is_operational_uuid(task_rating_id)),
    CONSTRAINT task_rating_statement_tenant_fk
        FOREIGN KEY (tenant_record_id, task_statement_id)
        REFERENCES task_statement(tenant_record_id, task_statement_id),
    CONSTRAINT task_rating_dimension_code_check
        CHECK (rating_dimension_code IN ('importance', 'criticality', 'frequency', 'duration', 'required_at_entry')),
    CONSTRAINT task_rating_scale_check
        CHECK (
            scale_maximum_value > scale_minimum_value
            AND rating_value BETWEEN scale_minimum_value AND scale_maximum_value
        ),
    CONSTRAINT task_rating_rater_group_code_check
        CHECK (rater_group_code COLLATE "C" ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'),
    CONSTRAINT task_rating_sample_size_check
        CHECK (sample_size_count > 0),
    CONSTRAINT task_rating_tenant_identity_unique
        UNIQUE (tenant_record_id, task_rating_id),
    CONSTRAINT task_rating_statement_dimension_group_unique
        UNIQUE (tenant_record_id, task_statement_id, rating_dimension_code, rater_group_code)
);

CREATE TABLE fja_function (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    fja_function_id uuid PRIMARY KEY,
    job_analysis_case_id uuid NOT NULL,
    function_dimension_code text NOT NULL,
    function_level_value numeric(10,4) NOT NULL,
    methodology_version_code text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT fja_function_operational_id_check
        CHECK (is_operational_uuid(fja_function_id)),
    CONSTRAINT fja_function_case_tenant_fk
        FOREIGN KEY (tenant_record_id, job_analysis_case_id)
        REFERENCES job_analysis_case(tenant_record_id, job_analysis_case_id),
    CONSTRAINT fja_function_dimension_code_check
        CHECK (
            function_dimension_code IN (
                'data',
                'people',
                'things',
                'reasoning',
                'mathematics',
                'language',
                'worker_instructions',
                'worker_technology',
                'worker_interaction',
                'human_error_consequence'
            )
        ),
    CONSTRAINT fja_function_level_check
        CHECK (function_level_value >= 0),
    CONSTRAINT fja_function_methodology_code_check
        CHECK (methodology_version_code COLLATE "C" ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'),
    CONSTRAINT fja_function_tenant_identity_unique
        UNIQUE (tenant_record_id, fja_function_id),
    CONSTRAINT fja_function_case_dimension_unique
        UNIQUE (tenant_record_id, job_analysis_case_id, function_dimension_code)
);

CREATE TABLE task_fja_link (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    task_fja_link_id uuid PRIMARY KEY,
    task_statement_id uuid NOT NULL,
    fja_function_id uuid NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT task_fja_link_operational_id_check
        CHECK (is_operational_uuid(task_fja_link_id)),
    CONSTRAINT task_fja_statement_tenant_fk
        FOREIGN KEY (tenant_record_id, task_statement_id)
        REFERENCES task_statement(tenant_record_id, task_statement_id),
    CONSTRAINT task_fja_function_tenant_fk
        FOREIGN KEY (tenant_record_id, fja_function_id)
        REFERENCES fja_function(tenant_record_id, fja_function_id),
    CONSTRAINT task_fja_link_tenant_identity_unique
        UNIQUE (tenant_record_id, task_fja_link_id),
    CONSTRAINT task_fja_membership_unique
        UNIQUE (tenant_record_id, task_statement_id, fja_function_id)
);

CREATE TABLE ksao_requirement (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    ksao_requirement_id uuid PRIMARY KEY,
    job_analysis_case_id uuid NOT NULL,
    ksao_type_code text NOT NULL,
    requirement_text text NOT NULL,
    required_at_entry boolean NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ksao_requirement_operational_id_check
        CHECK (is_operational_uuid(ksao_requirement_id)),
    CONSTRAINT ksao_requirement_case_tenant_fk
        FOREIGN KEY (tenant_record_id, job_analysis_case_id)
        REFERENCES job_analysis_case(tenant_record_id, job_analysis_case_id),
    CONSTRAINT ksao_requirement_type_code_check
        CHECK (ksao_type_code IN ('knowledge', 'skill', 'ability', 'other_characteristic')),
    CONSTRAINT ksao_requirement_text_check
        CHECK (length(btrim(requirement_text)) BETWEEN 10 AND 4000),
    CONSTRAINT ksao_requirement_tenant_identity_unique
        UNIQUE (tenant_record_id, ksao_requirement_id)
);

CREATE TABLE task_ksao_link (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    task_ksao_link_id uuid PRIMARY KEY,
    task_statement_id uuid NOT NULL,
    ksao_requirement_id uuid NOT NULL,
    linkage_strength_value numeric(10,4) NOT NULL,
    linkage_method_code text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT task_ksao_link_operational_id_check
        CHECK (is_operational_uuid(task_ksao_link_id)),
    CONSTRAINT task_ksao_statement_tenant_fk
        FOREIGN KEY (tenant_record_id, task_statement_id)
        REFERENCES task_statement(tenant_record_id, task_statement_id),
    CONSTRAINT task_ksao_requirement_tenant_fk
        FOREIGN KEY (tenant_record_id, ksao_requirement_id)
        REFERENCES ksao_requirement(tenant_record_id, ksao_requirement_id),
    CONSTRAINT task_ksao_strength_check
        CHECK (linkage_strength_value >= 0),
    CONSTRAINT task_ksao_method_code_check
        CHECK (linkage_method_code COLLATE "C" ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'),
    CONSTRAINT task_ksao_link_tenant_identity_unique
        UNIQUE (tenant_record_id, task_ksao_link_id),
    CONSTRAINT task_ksao_membership_unique
        UNIQUE (tenant_record_id, task_statement_id, ksao_requirement_id)
);

CREATE TABLE job_analysis_approval_record (
    tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id),
    job_analysis_approval_record_id uuid PRIMARY KEY,
    job_analysis_case_id uuid NOT NULL,
    approver_reference text NOT NULL,
    approval_reason text NOT NULL,
    evidence_version_code text NOT NULL,
    analysis_content_sha256 text NOT NULL,
    approved_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT job_analysis_approval_operational_id_check
        CHECK (is_operational_uuid(job_analysis_approval_record_id)),
    CONSTRAINT job_analysis_approval_case_tenant_fk
        FOREIGN KEY (tenant_record_id, job_analysis_case_id)
        REFERENCES job_analysis_case(tenant_record_id, job_analysis_case_id),
    CONSTRAINT job_analysis_approver_reference_check
        CHECK (approver_reference COLLATE "C" ~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$'),
    CONSTRAINT job_analysis_approval_reason_check
        CHECK (length(btrim(approval_reason)) BETWEEN 10 AND 4000),
    CONSTRAINT job_analysis_approval_evidence_version_check
        CHECK (evidence_version_code COLLATE "C" ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'),
    CONSTRAINT job_analysis_approval_digest_check
        CHECK (analysis_content_sha256 COLLATE "C" ~ '^[0-9a-f]{64}$'),
    CONSTRAINT job_analysis_approval_recorded_check
        CHECK (recorded_at >= approved_at),
    CONSTRAINT job_analysis_approval_tenant_identity_unique
        UNIQUE (tenant_record_id, job_analysis_approval_record_id),
    CONSTRAINT job_analysis_case_single_approval_unique
        UNIQUE (tenant_record_id, job_analysis_case_id)
);

CREATE FUNCTION job_analysis_case_is_approved(
    p_tenant_record_id uuid,
    p_job_analysis_case_id uuid
)
RETURNS boolean
LANGUAGE sql
STABLE
PARALLEL SAFE
SET search_path = pg_catalog, public, pg_temp
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.job_analysis_approval_record AS approval_record
        WHERE approval_record.tenant_record_id = p_tenant_record_id
          AND approval_record.job_analysis_case_id = p_job_analysis_case_id
    )
$$;

CREATE FUNCTION calculate_job_analysis_content_sha256(
    p_tenant_record_id uuid,
    p_job_analysis_case_id uuid
)
RETURNS text
LANGUAGE plpgsql
STABLE
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    canonical_content jsonb;
BEGIN
    SELECT pg_catalog.jsonb_build_object(
        'case', pg_catalog.jsonb_build_object(
            'job_analysis_case_id', analysis_case.job_analysis_case_id,
            'job_profile_id', analysis_case.job_profile_id,
            'analysis_version_code', analysis_case.analysis_version_code,
            'analysis_method_code', analysis_case.analysis_method_code,
            'analyst_reference', analysis_case.analyst_reference,
            'effective_from', analysis_case.effective_from,
            'effective_to', analysis_case.effective_to,
            'recorded_at', analysis_case.recorded_at
        ),
        'sources', COALESCE((
            SELECT pg_catalog.jsonb_agg(
                pg_catalog.jsonb_build_object(
                    'source_record_id', source_header.source_record_id,
                    'source_type_code', source_header.source_type_code,
                    'source_locator', source_header.source_locator,
                    'source_title', source_header.source_title,
                    'publisher_name', source_header.publisher_name,
                    'source_version_id', source_snapshot.source_version_id,
                    'source_version_code', source_snapshot.source_version_code,
                    'source_content_sha256', source_snapshot.source_content_sha256,
                    'captured_at', source_snapshot.captured_at,
                    'evidence_role_code', source_link.evidence_role_code,
                    'source_span_reference', source_link.source_span_reference
                ) ORDER BY source_link.job_analysis_source_link_id::text COLLATE "C"
            )
            FROM public.job_analysis_source_link AS source_link
            JOIN public.source_version AS source_snapshot
              ON source_snapshot.tenant_record_id = source_link.tenant_record_id
             AND source_snapshot.source_version_id = source_link.source_version_id
            JOIN public.source_record AS source_header
              ON source_header.tenant_record_id = source_snapshot.tenant_record_id
             AND source_header.source_record_id = source_snapshot.source_record_id
            WHERE source_link.tenant_record_id = p_tenant_record_id
              AND source_link.job_analysis_case_id = p_job_analysis_case_id
        ), '[]'::jsonb),
        'tasks', COALESCE((
            SELECT pg_catalog.jsonb_agg(
                pg_catalog.jsonb_build_object(
                    'task_statement_id', task.task_statement_id,
                    'task_sequence_number', task.task_sequence_number,
                    'task_text', task.task_text,
                    'recorded_at', task.recorded_at
                ) ORDER BY task.task_sequence_number, task.task_statement_id::text COLLATE "C"
            )
            FROM public.task_statement AS task
            WHERE task.tenant_record_id = p_tenant_record_id
              AND task.job_analysis_case_id = p_job_analysis_case_id
        ), '[]'::jsonb),
        'task_ratings', COALESCE((
            SELECT pg_catalog.jsonb_agg(
                pg_catalog.jsonb_build_object(
                    'task_rating_id', rating.task_rating_id,
                    'task_statement_id', rating.task_statement_id,
                    'rating_dimension_code', rating.rating_dimension_code,
                    'rating_value', rating.rating_value,
                    'scale_minimum_value', rating.scale_minimum_value,
                    'scale_maximum_value', rating.scale_maximum_value,
                    'rater_group_code', rating.rater_group_code,
                    'sample_size_count', rating.sample_size_count
                ) ORDER BY rating.task_rating_id::text COLLATE "C"
            )
            FROM public.task_rating AS rating
            JOIN public.task_statement AS task
              ON task.tenant_record_id = rating.tenant_record_id
             AND task.task_statement_id = rating.task_statement_id
            WHERE task.tenant_record_id = p_tenant_record_id
              AND task.job_analysis_case_id = p_job_analysis_case_id
        ), '[]'::jsonb),
        'fja_functions', COALESCE((
            SELECT pg_catalog.jsonb_agg(
                pg_catalog.jsonb_build_object(
                    'fja_function_id', fja.fja_function_id,
                    'function_dimension_code', fja.function_dimension_code,
                    'function_level_value', fja.function_level_value,
                    'methodology_version_code', fja.methodology_version_code
                ) ORDER BY fja.fja_function_id::text COLLATE "C"
            )
            FROM public.fja_function AS fja
            WHERE fja.tenant_record_id = p_tenant_record_id
              AND fja.job_analysis_case_id = p_job_analysis_case_id
        ), '[]'::jsonb),
        'task_fja_links', COALESCE((
            SELECT pg_catalog.jsonb_agg(
                pg_catalog.jsonb_build_object(
                    'task_statement_id', task_fja.task_statement_id,
                    'fja_function_id', task_fja.fja_function_id
                ) ORDER BY task_fja.task_fja_link_id::text COLLATE "C"
            )
            FROM public.task_fja_link AS task_fja
            JOIN public.task_statement AS task
              ON task.tenant_record_id = task_fja.tenant_record_id
             AND task.task_statement_id = task_fja.task_statement_id
            WHERE task.tenant_record_id = p_tenant_record_id
              AND task.job_analysis_case_id = p_job_analysis_case_id
        ), '[]'::jsonb),
        'ksao_requirements', COALESCE((
            SELECT pg_catalog.jsonb_agg(
                pg_catalog.jsonb_build_object(
                    'ksao_requirement_id', ksao.ksao_requirement_id,
                    'ksao_type_code', ksao.ksao_type_code,
                    'requirement_text', ksao.requirement_text,
                    'required_at_entry', ksao.required_at_entry
                ) ORDER BY ksao.ksao_requirement_id::text COLLATE "C"
            )
            FROM public.ksao_requirement AS ksao
            WHERE ksao.tenant_record_id = p_tenant_record_id
              AND ksao.job_analysis_case_id = p_job_analysis_case_id
        ), '[]'::jsonb),
        'task_ksao_links', COALESCE((
            SELECT pg_catalog.jsonb_agg(
                pg_catalog.jsonb_build_object(
                    'task_statement_id', task_ksao.task_statement_id,
                    'ksao_requirement_id', task_ksao.ksao_requirement_id,
                    'linkage_strength_value', task_ksao.linkage_strength_value,
                    'linkage_method_code', task_ksao.linkage_method_code
                ) ORDER BY task_ksao.task_ksao_link_id::text COLLATE "C"
            )
            FROM public.task_ksao_link AS task_ksao
            JOIN public.task_statement AS task
              ON task.tenant_record_id = task_ksao.tenant_record_id
             AND task.task_statement_id = task_ksao.task_statement_id
            WHERE task.tenant_record_id = p_tenant_record_id
              AND task.job_analysis_case_id = p_job_analysis_case_id
        ), '[]'::jsonb)
    )
    INTO canonical_content
    FROM public.job_analysis_case AS analysis_case
    WHERE analysis_case.tenant_record_id = p_tenant_record_id
      AND analysis_case.job_analysis_case_id = p_job_analysis_case_id;

    IF canonical_content IS NULL THEN
        RAISE EXCEPTION 'job analysis case does not exist in the tenant'
            USING ERRCODE = '23503';
    END IF;

    RETURN pg_catalog.encode(
        public.digest(pg_catalog.convert_to(canonical_content::text, 'UTF8'), 'sha256'),
        'hex'
    );
END;
$$;

CREATE FUNCTION protect_job_analysis_direct_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    PERFORM 1
    FROM public.job_analysis_case AS analysis_case
    WHERE analysis_case.tenant_record_id = NEW.tenant_record_id
      AND analysis_case.job_analysis_case_id = NEW.job_analysis_case_id
    FOR SHARE OF analysis_case;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'job analysis case does not exist in the tenant'
            USING ERRCODE = '23503';
    END IF;

    IF public.job_analysis_case_is_approved(
        NEW.tenant_record_id,
        NEW.job_analysis_case_id
    ) THEN
        RAISE EXCEPTION 'approved job analysis case is sealed'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION protect_job_analysis_task_child_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    owning_case_id uuid;
BEGIN
    SELECT task.job_analysis_case_id
    INTO owning_case_id
    FROM public.task_statement AS task
    WHERE task.tenant_record_id = NEW.tenant_record_id
      AND task.task_statement_id = NEW.task_statement_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'job analysis task does not exist in the tenant'
            USING ERRCODE = '23503';
    END IF;

    PERFORM 1
    FROM public.job_analysis_case AS analysis_case
    WHERE analysis_case.tenant_record_id = NEW.tenant_record_id
      AND analysis_case.job_analysis_case_id = owning_case_id
    FOR SHARE OF analysis_case;

    IF public.job_analysis_case_is_approved(NEW.tenant_record_id, owning_case_id) THEN
        RAISE EXCEPTION 'approved job analysis case is sealed'
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$$;

CREATE FUNCTION validate_task_fja_link()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    task_case_id uuid;
    function_case_id uuid;
BEGIN
    SELECT task.job_analysis_case_id
    INTO task_case_id
    FROM public.task_statement AS task
    WHERE task.tenant_record_id = NEW.tenant_record_id
      AND task.task_statement_id = NEW.task_statement_id;

    SELECT fja.job_analysis_case_id
    INTO function_case_id
    FROM public.fja_function AS fja
    WHERE fja.tenant_record_id = NEW.tenant_record_id
      AND fja.fja_function_id = NEW.fja_function_id;

    IF task_case_id IS NULL OR function_case_id IS NULL THEN
        RAISE EXCEPTION 'task and FJA function must exist in the tenant'
            USING ERRCODE = '23503';
    END IF;
    IF task_case_id IS DISTINCT FROM function_case_id THEN
        RAISE EXCEPTION 'task and FJA function must belong to the same job analysis case'
            USING ERRCODE = '23514';
    END IF;

    PERFORM 1
    FROM public.job_analysis_case AS analysis_case
    WHERE analysis_case.tenant_record_id = NEW.tenant_record_id
      AND analysis_case.job_analysis_case_id = task_case_id
    FOR SHARE OF analysis_case;

    IF public.job_analysis_case_is_approved(NEW.tenant_record_id, task_case_id) THEN
        RAISE EXCEPTION 'approved job analysis case is sealed'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION validate_task_ksao_link()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    task_case_id uuid;
    requirement_case_id uuid;
BEGIN
    SELECT task.job_analysis_case_id
    INTO task_case_id
    FROM public.task_statement AS task
    WHERE task.tenant_record_id = NEW.tenant_record_id
      AND task.task_statement_id = NEW.task_statement_id;

    SELECT ksao.job_analysis_case_id
    INTO requirement_case_id
    FROM public.ksao_requirement AS ksao
    WHERE ksao.tenant_record_id = NEW.tenant_record_id
      AND ksao.ksao_requirement_id = NEW.ksao_requirement_id;

    IF task_case_id IS NULL OR requirement_case_id IS NULL THEN
        RAISE EXCEPTION 'task and KSAO requirement must exist in the tenant'
            USING ERRCODE = '23503';
    END IF;
    IF task_case_id IS DISTINCT FROM requirement_case_id THEN
        RAISE EXCEPTION 'task and KSAO requirement must belong to the same job analysis case'
            USING ERRCODE = '23514';
    END IF;

    PERFORM 1
    FROM public.job_analysis_case AS analysis_case
    WHERE analysis_case.tenant_record_id = NEW.tenant_record_id
      AND analysis_case.job_analysis_case_id = task_case_id
    FOR SHARE OF analysis_case;

    IF public.job_analysis_case_is_approved(NEW.tenant_record_id, task_case_id) THEN
        RAISE EXCEPTION 'approved job analysis case is sealed'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION seal_job_analysis_case()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    analysis_recorded_at timestamptz;
BEGIN
    IF NEW.analysis_content_sha256 IS NOT NULL THEN
        RAISE EXCEPTION 'job analysis approval digest is database-owned'
            USING ERRCODE = '22023';
    END IF;

    -- The case row is the serialization boundary for evidence mutation versus
    -- approval. Content inserts take FOR SHARE; approval takes FOR UPDATE. An
    -- insert that started first must commit before the digest is observed, and
    -- an insert that starts after approval waits and then sees the sealed row.
    SELECT analysis_case.recorded_at
    INTO analysis_recorded_at
    FROM public.job_analysis_case AS analysis_case
    WHERE analysis_case.tenant_record_id = NEW.tenant_record_id
      AND analysis_case.job_analysis_case_id = NEW.job_analysis_case_id
    FOR UPDATE OF analysis_case;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'job analysis case does not exist in the tenant'
            USING ERRCODE = '23503';
    END IF;
    IF NEW.approved_at < analysis_recorded_at THEN
        RAISE EXCEPTION 'job analysis approval cannot predate the analysis case'
            USING ERRCODE = '23514';
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM public.job_analysis_source_link AS source_link
        WHERE source_link.tenant_record_id = NEW.tenant_record_id
          AND source_link.job_analysis_case_id = NEW.job_analysis_case_id
    ) THEN
        RAISE EXCEPTION 'job analysis approval requires at least one linked source version'
            USING ERRCODE = '23514';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM public.job_analysis_source_link AS source_link
        JOIN public.source_version AS source_snapshot
          ON source_snapshot.tenant_record_id = source_link.tenant_record_id
         AND source_snapshot.source_version_id = source_link.source_version_id
        JOIN public.source_record AS source_header
          ON source_header.tenant_record_id = source_snapshot.tenant_record_id
         AND source_header.source_record_id = source_snapshot.source_record_id
        WHERE source_link.tenant_record_id = NEW.tenant_record_id
          AND source_link.job_analysis_case_id = NEW.job_analysis_case_id
          AND source_header.source_type_code = 'llm_draft'
    ) THEN
        RAISE EXCEPTION 'approved job analysis cannot include LLM draft evidence'
            USING ERRCODE = '23514';
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM public.task_statement AS task
        WHERE task.tenant_record_id = NEW.tenant_record_id
          AND task.job_analysis_case_id = NEW.job_analysis_case_id
    ) THEN
        RAISE EXCEPTION 'job analysis approval requires at least one task statement'
            USING ERRCODE = '23514';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM public.task_statement AS task
        WHERE task.tenant_record_id = NEW.tenant_record_id
          AND task.job_analysis_case_id = NEW.job_analysis_case_id
          AND (
              NOT EXISTS (
                  SELECT 1
                  FROM public.task_fja_link AS task_fja
                  WHERE task_fja.tenant_record_id = task.tenant_record_id
                    AND task_fja.task_statement_id = task.task_statement_id
              )
              OR NOT EXISTS (
                  SELECT 1
                  FROM public.task_ksao_link AS task_ksao
                  WHERE task_ksao.tenant_record_id = task.tenant_record_id
                    AND task_ksao.task_statement_id = task.task_statement_id
              )
          )
    ) THEN
        RAISE EXCEPTION 'job analysis approval requires every task to link FJA and KSAO evidence'
            USING ERRCODE = '23514';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM public.task_statement AS task
        WHERE task.tenant_record_id = NEW.tenant_record_id
          AND task.job_analysis_case_id = NEW.job_analysis_case_id
          AND NOT EXISTS (
              SELECT 1
              FROM public.task_rating AS rating
              WHERE rating.tenant_record_id = task.tenant_record_id
                AND rating.task_statement_id = task.task_statement_id
                AND rating.rating_dimension_code IN ('importance', 'criticality')
          )
    ) THEN
        RAISE EXCEPTION 'job analysis approval requires importance or criticality evidence for every task'
            USING ERRCODE = '23514';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM public.ksao_requirement AS ksao
        WHERE ksao.tenant_record_id = NEW.tenant_record_id
          AND ksao.job_analysis_case_id = NEW.job_analysis_case_id
          AND NOT EXISTS (
              SELECT 1
              FROM public.task_ksao_link AS task_ksao
              WHERE task_ksao.tenant_record_id = ksao.tenant_record_id
                AND task_ksao.ksao_requirement_id = ksao.ksao_requirement_id
          )
    ) THEN
        RAISE EXCEPTION 'job analysis approval requires every KSAO to link at least one task'
            USING ERRCODE = '23514';
    END IF;

    NEW.analysis_content_sha256 := public.calculate_job_analysis_content_sha256(
        NEW.tenant_record_id,
        NEW.job_analysis_case_id
    );
    RETURN NEW;
END;
$$;

CREATE FUNCTION reject_job_analysis_truncate()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'job analysis evidence cannot be truncated'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER job_analysis_source_seal_guard
BEFORE INSERT ON job_analysis_source_link
FOR EACH ROW EXECUTE FUNCTION protect_job_analysis_direct_insert();
CREATE TRIGGER task_statement_seal_guard
BEFORE INSERT ON task_statement
FOR EACH ROW EXECUTE FUNCTION protect_job_analysis_direct_insert();
CREATE TRIGGER fja_function_seal_guard
BEFORE INSERT ON fja_function
FOR EACH ROW EXECUTE FUNCTION protect_job_analysis_direct_insert();
CREATE TRIGGER ksao_requirement_seal_guard
BEFORE INSERT ON ksao_requirement
FOR EACH ROW EXECUTE FUNCTION protect_job_analysis_direct_insert();
CREATE TRIGGER task_rating_seal_guard
BEFORE INSERT ON task_rating
FOR EACH ROW EXECUTE FUNCTION protect_job_analysis_task_child_insert();
CREATE TRIGGER task_fja_same_case_guard
BEFORE INSERT ON task_fja_link
FOR EACH ROW EXECUTE FUNCTION validate_task_fja_link();
CREATE TRIGGER task_ksao_same_case_guard
BEFORE INSERT ON task_ksao_link
FOR EACH ROW EXECUTE FUNCTION validate_task_ksao_link();
CREATE TRIGGER job_analysis_approval_seal_guard
BEFORE INSERT ON job_analysis_approval_record
FOR EACH ROW EXECUTE FUNCTION seal_job_analysis_case();

CREATE TRIGGER source_record_append_only_guard
BEFORE UPDATE OR DELETE ON source_record
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER source_version_append_only_guard
BEFORE UPDATE OR DELETE ON source_version
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER job_analysis_case_append_only_guard
BEFORE UPDATE OR DELETE ON job_analysis_case
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER job_analysis_source_link_append_only_guard
BEFORE UPDATE OR DELETE ON job_analysis_source_link
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER task_statement_append_only_guard
BEFORE UPDATE OR DELETE ON task_statement
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER task_rating_append_only_guard
BEFORE UPDATE OR DELETE ON task_rating
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER fja_function_append_only_guard
BEFORE UPDATE OR DELETE ON fja_function
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER task_fja_link_append_only_guard
BEFORE UPDATE OR DELETE ON task_fja_link
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER ksao_requirement_append_only_guard
BEFORE UPDATE OR DELETE ON ksao_requirement
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER task_ksao_link_append_only_guard
BEFORE UPDATE OR DELETE ON task_ksao_link
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER job_analysis_approval_append_only_guard
BEFORE UPDATE OR DELETE ON job_analysis_approval_record
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

CREATE TRIGGER source_record_truncate_guard
BEFORE TRUNCATE ON source_record FOR EACH STATEMENT EXECUTE FUNCTION reject_job_analysis_truncate();
CREATE TRIGGER source_version_truncate_guard
BEFORE TRUNCATE ON source_version FOR EACH STATEMENT EXECUTE FUNCTION reject_job_analysis_truncate();
CREATE TRIGGER job_analysis_case_truncate_guard
BEFORE TRUNCATE ON job_analysis_case FOR EACH STATEMENT EXECUTE FUNCTION reject_job_analysis_truncate();
CREATE TRIGGER job_analysis_source_link_truncate_guard
BEFORE TRUNCATE ON job_analysis_source_link FOR EACH STATEMENT EXECUTE FUNCTION reject_job_analysis_truncate();
CREATE TRIGGER task_statement_truncate_guard
BEFORE TRUNCATE ON task_statement FOR EACH STATEMENT EXECUTE FUNCTION reject_job_analysis_truncate();
CREATE TRIGGER task_rating_truncate_guard
BEFORE TRUNCATE ON task_rating FOR EACH STATEMENT EXECUTE FUNCTION reject_job_analysis_truncate();
CREATE TRIGGER fja_function_truncate_guard
BEFORE TRUNCATE ON fja_function FOR EACH STATEMENT EXECUTE FUNCTION reject_job_analysis_truncate();
CREATE TRIGGER task_fja_link_truncate_guard
BEFORE TRUNCATE ON task_fja_link FOR EACH STATEMENT EXECUTE FUNCTION reject_job_analysis_truncate();
CREATE TRIGGER ksao_requirement_truncate_guard
BEFORE TRUNCATE ON ksao_requirement FOR EACH STATEMENT EXECUTE FUNCTION reject_job_analysis_truncate();
CREATE TRIGGER task_ksao_link_truncate_guard
BEFORE TRUNCATE ON task_ksao_link FOR EACH STATEMENT EXECUTE FUNCTION reject_job_analysis_truncate();
CREATE TRIGGER job_analysis_approval_truncate_guard
BEFORE TRUNCATE ON job_analysis_approval_record FOR EACH STATEMENT EXECUTE FUNCTION reject_job_analysis_truncate();

ALTER TABLE source_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_record FORCE ROW LEVEL SECURITY;
CREATE POLICY source_record_scope_policy ON source_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE source_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_version FORCE ROW LEVEL SECURITY;
CREATE POLICY source_version_scope_policy ON source_version
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE job_analysis_case ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_analysis_case FORCE ROW LEVEL SECURITY;
CREATE POLICY job_analysis_case_scope_policy ON job_analysis_case
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE job_analysis_source_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_analysis_source_link FORCE ROW LEVEL SECURITY;
CREATE POLICY job_analysis_source_scope_policy ON job_analysis_source_link
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE task_statement ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_statement FORCE ROW LEVEL SECURITY;
CREATE POLICY task_statement_scope_policy ON task_statement
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE task_rating ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_rating FORCE ROW LEVEL SECURITY;
CREATE POLICY task_rating_scope_policy ON task_rating
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE fja_function ENABLE ROW LEVEL SECURITY;
ALTER TABLE fja_function FORCE ROW LEVEL SECURITY;
CREATE POLICY fja_function_scope_policy ON fja_function
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE task_fja_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_fja_link FORCE ROW LEVEL SECURITY;
CREATE POLICY task_fja_link_scope_policy ON task_fja_link
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE ksao_requirement ENABLE ROW LEVEL SECURITY;
ALTER TABLE ksao_requirement FORCE ROW LEVEL SECURITY;
CREATE POLICY ksao_requirement_scope_policy ON ksao_requirement
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE task_ksao_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_ksao_link FORCE ROW LEVEL SECURITY;
CREATE POLICY task_ksao_link_scope_policy ON task_ksao_link
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

ALTER TABLE job_analysis_approval_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_analysis_approval_record FORCE ROW LEVEL SECURITY;
CREATE POLICY job_analysis_approval_scope_policy ON job_analysis_approval_record
USING (tenant_record_id = current_tenant_record_id())
WITH CHECK (tenant_record_id = current_tenant_record_id());

REVOKE TRUNCATE ON source_record, source_version, job_analysis_case,
    job_analysis_source_link, task_statement, task_rating, fja_function,
    task_fja_link, ksao_requirement, task_ksao_link,
    job_analysis_approval_record FROM PUBLIC;

COMMIT;
