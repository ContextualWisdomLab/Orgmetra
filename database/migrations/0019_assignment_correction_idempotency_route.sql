-- Extend the durable People mutation replay vocabulary for Assignment category corrections.
--
-- Correction retries reuse the existing tenant-scoped idempotency ledger. The
-- semantic digest is bound to the predecessor and reviewed correction meaning,
-- while created_record_id stores the first committed replacement Assignment.

BEGIN;

SET LOCAL search_path = public, pg_catalog;

ALTER TABLE public.people_mutation_idempotency_record
    DROP CONSTRAINT people_mutation_idempotency_route_check;

ALTER TABLE public.people_mutation_idempotency_record
    ADD CONSTRAINT people_mutation_idempotency_route_check
    CHECK (
        command_route IN (
            'candidate-worker-conversions',
            'employment-records',
            'position-records',
            'assignment-records',
            'assignment-category-corrections'
        )
    ) NOT VALID;

ALTER TABLE public.people_mutation_idempotency_record
    VALIDATE CONSTRAINT people_mutation_idempotency_route_check;

COMMIT;
