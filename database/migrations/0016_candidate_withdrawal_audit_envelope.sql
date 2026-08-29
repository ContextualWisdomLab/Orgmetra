-- Extend the already-deployed audit envelope validator through a forward-only
-- migration. Do not edit 0008: existing databases must receive this change.

BEGIN;

SET LOCAL search_path = public, pg_catalog;

CREATE OR REPLACE FUNCTION public.validate_audit_event_envelope(
    p_canonical_event_json text,
    p_audit_event_record_id uuid,
    p_tenant_record_id uuid,
    p_event_envelope_digest text
)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
STRICT
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    event_envelope jsonb;
    event_data jsonb;
    event_keys text[];
    data_keys text[];
    event_high_impact boolean;
    event_time_text text;
    event_year integer;
    event_month integer;
    event_day integer;
    event_hour integer;
    event_minute integer;
    event_second integer;
    expected_keys_without_confirmation constant text[] := ARRAY[
        'data',
        'datacontenttype',
        'id',
        'orgmetraactor',
        'orgmetraevidence',
        'orgmetrapurpose',
        'orgmetrareason',
        'orgmetratenant',
        'source',
        'specversion',
        'subject',
        'time',
        'type'
    ];
    expected_keys_with_confirmation constant text[] := ARRAY[
        'data',
        'datacontenttype',
        'id',
        'orgmetraactor',
        'orgmetraconfirmation',
        'orgmetraevidence',
        'orgmetrapurpose',
        'orgmetrareason',
        'orgmetratenant',
        'source',
        'specversion',
        'subject',
        'time',
        'type'
    ];
    candidate_withdrawal_data_keys constant text[] := ARRAY[
        'evidence_version',
        'high_impact',
        'identity_resolution_digest',
        'identity_resolution_reference',
        'result_code',
        'withdrawal_evidence_digest'
    ];
BEGIN
    IF public.is_operational_uuid(p_audit_event_record_id) IS NOT TRUE
       OR public.is_operational_uuid(p_tenant_record_id) IS NOT TRUE THEN
        RETURN false;
    END IF;

    BEGIN
        event_envelope := p_canonical_event_json::jsonb;
    EXCEPTION
        WHEN others THEN
            RETURN false;
    END;

    IF pg_catalog.jsonb_typeof(event_envelope) <> 'object' THEN
        RETURN false;
    END IF;

    SELECT pg_catalog.array_agg(event_key ORDER BY event_key COLLATE "C")
    INTO event_keys
    FROM pg_catalog.jsonb_object_keys(event_envelope) AS event_key_set(event_key);

    IF event_keys IS NULL
       OR (
           event_keys IS DISTINCT FROM expected_keys_without_confirmation
           AND event_keys IS DISTINCT FROM expected_keys_with_confirmation
       ) THEN
        RETURN false;
    END IF;

    event_data := event_envelope -> 'data';
    IF pg_catalog.jsonb_typeof(event_data) <> 'object' THEN
        RETURN false;
    END IF;

    SELECT pg_catalog.array_agg(data_key ORDER BY data_key COLLATE "C")
    INTO data_keys
    FROM pg_catalog.jsonb_object_keys(event_data) AS data_key_set(data_key);
    IF event_envelope ->> 'source' = 'urn:orgmetra:talent_acquisition'
       AND event_envelope ->> 'type' = 'orgmetra.candidate.application_withdrawn' THEN
        IF data_keys IS DISTINCT FROM candidate_withdrawal_data_keys THEN
            RETURN false;
        END IF;
    ELSIF data_keys IS DISTINCT FROM ARRAY['high_impact', 'result_code']::text[] THEN
        RETURN false;
    END IF;

    IF event_envelope ->> 'specversion' <> '1.0'
       OR event_envelope ->> 'datacontenttype' <> 'application/json'
       OR event_envelope ->> 'id' <> p_audit_event_record_id::text
       OR event_envelope ->> 'orgmetratenant' <> p_tenant_record_id::text THEN
        RETURN false;
    END IF;

    IF pg_catalog.jsonb_typeof(event_envelope -> 'id') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'source') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'type') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'subject') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'time') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'orgmetraactor') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'orgmetrapurpose') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'orgmetrareason') <> 'string'
       OR pg_catalog.jsonb_typeof(event_envelope -> 'orgmetraevidence') <> 'string'
       OR pg_catalog.jsonb_typeof(event_data -> 'result_code') <> 'string'
       OR pg_catalog.jsonb_typeof(event_data -> 'high_impact') <> 'boolean' THEN
        RETURN false;
    END IF;

    IF (event_envelope ->> 'source') COLLATE "C"
            !~ '^urn:orgmetra:[a-z][a-z0-9]*(?:_[a-z0-9]+)+$'
       OR (event_envelope ->> 'type') COLLATE "C"
            !~ '^orgmetra(?:\.[a-z][a-z0-9_]*){2,}$'
       OR (event_envelope ->> 'subject') COLLATE "C"
            !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$'
       OR (event_envelope ->> 'orgmetraactor') COLLATE "C"
            !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$'
       OR (event_envelope ->> 'orgmetrapurpose') COLLATE "C"
            !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
       OR (event_envelope ->> 'orgmetrareason') COLLATE "C"
            !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
       OR (event_envelope ->> 'orgmetraevidence') COLLATE "C"
            !~ '^[A-Za-z0-9][A-Za-z0-9._:-]*$'
       OR (event_data ->> 'result_code') COLLATE "C"
            !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$' THEN
        RETURN false;
    END IF;

    IF event_envelope ->> 'source' = 'urn:orgmetra:talent_acquisition'
       AND event_envelope ->> 'type' = 'orgmetra.candidate.application_withdrawn'
       AND (
           pg_catalog.jsonb_typeof(event_data -> 'evidence_version')
               IS DISTINCT FROM 'number'
           OR (event_data ->> 'evidence_version') IS NULL
           OR (
               CASE
                   WHEN (event_data ->> 'evidence_version') COLLATE "C"
                            ~ '^[1-9][0-9]{0,6}$'
                   THEN (event_data ->> 'evidence_version')::integer
                            BETWEEN 1 AND 1000000
                   ELSE false
               END
           ) IS NOT TRUE
           OR pg_catalog.jsonb_typeof(event_data -> 'identity_resolution_reference')
               IS DISTINCT FROM 'string'
           OR (event_data ->> 'identity_resolution_reference') IS NULL
           OR (event_data ->> 'identity_resolution_reference') COLLATE "C"
               !~ '^identity_resolution:[A-Za-z0-9][A-Za-z0-9._~-]*$'
           OR pg_catalog.jsonb_typeof(event_data -> 'identity_resolution_digest')
               IS DISTINCT FROM 'string'
           OR (event_data ->> 'identity_resolution_digest') IS NULL
           OR (event_data ->> 'identity_resolution_digest') COLLATE "C"
               !~ '^[0-9a-f]{64}$'
           OR pg_catalog.jsonb_typeof(event_data -> 'withdrawal_evidence_digest')
               IS DISTINCT FROM 'string'
           OR (event_data ->> 'withdrawal_evidence_digest') IS NULL
           OR (event_data ->> 'withdrawal_evidence_digest') COLLATE "C"
               !~ '^[0-9a-f]{64}$'
       ) THEN
        RETURN false;
    END IF;

    event_time_text := event_envelope ->> 'time';
    IF event_time_text COLLATE "C"
            !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$' THEN
        RETURN false;
    END IF;

    BEGIN
        event_year := pg_catalog.substr(event_time_text, 1, 4)::integer;
        event_month := pg_catalog.substr(event_time_text, 6, 2)::integer;
        event_day := pg_catalog.substr(event_time_text, 9, 2)::integer;
        event_hour := pg_catalog.substr(event_time_text, 12, 2)::integer;
        event_minute := pg_catalog.substr(event_time_text, 15, 2)::integer;
        event_second := pg_catalog.substr(event_time_text, 18, 2)::integer;
        PERFORM pg_catalog.make_date(event_year, event_month, event_day);
    EXCEPTION
        WHEN others THEN
            RETURN false;
    END;

    IF event_hour > 23 OR event_minute > 59 OR event_second > 59 THEN
        RETURN false;
    END IF;

    event_high_impact := (event_data ->> 'high_impact')::boolean;
    IF event_high_impact THEN
        IF NOT (event_envelope ? 'orgmetraconfirmation')
           OR pg_catalog.jsonb_typeof(event_envelope -> 'orgmetraconfirmation') <> 'string'
           OR (event_envelope ->> 'orgmetraconfirmation') COLLATE "C"
              !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$' THEN
            RETURN false;
        END IF;
    ELSIF event_envelope ? 'orgmetraconfirmation' THEN
        IF pg_catalog.jsonb_typeof(event_envelope -> 'orgmetraconfirmation') <> 'string'
           OR (event_envelope ->> 'orgmetraconfirmation') COLLATE "C"
              !~ '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$' THEN
            RETURN false;
        END IF;
    END IF;

    IF p_event_envelope_digest COLLATE "C" !~ '^[0-9a-f]{64}$'
       OR pg_catalog.encode(
            public.digest(pg_catalog.convert_to(p_canonical_event_json, 'UTF8'), 'sha256'),
            'hex'
          ) <> p_event_envelope_digest THEN
        RETURN false;
    END IF;

    RETURN true;
END;
$$;

COMMIT;
