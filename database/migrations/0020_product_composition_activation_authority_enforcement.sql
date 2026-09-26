-- Make external authorization evidence mandatory for every durable composition activation.
-- Migration/fault fixtures may exercise the lower structural registry against the predecessor
-- schema, but the current production schema must never admit a deployment transition that is
-- not attributable to an exact durable evidence bundle.
-- Fence activation-event writers before inspecting predecessor history so no structural event
-- can commit between the preflight and publication of the NOT NULL authority boundary.

BEGIN;

LOCK TABLE public.product_composition_activation_event IN SHARE ROW EXCLUSIVE MODE;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM public.product_composition_activation_event
        WHERE evidence_bundle_sha256 IS NULL
    ) THEN
        RAISE EXCEPTION
            'cannot enforce authorized activation while structural events exist';
    END IF;
END;
$$;

ALTER TABLE public.product_composition_activation_event
    ALTER COLUMN evidence_bundle_sha256 SET NOT NULL;

COMMIT;
