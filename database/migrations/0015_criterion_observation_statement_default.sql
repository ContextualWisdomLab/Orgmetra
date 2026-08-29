-- Record omitted criterion-observation timestamps at statement time.
-- The transaction timestamp can precede a real observation in a long transaction.

ALTER TABLE criterion_observation
ALTER COLUMN recorded_from SET DEFAULT statement_timestamp();
