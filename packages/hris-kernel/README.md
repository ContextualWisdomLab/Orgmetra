# Orgmetra HRIS kernel

Pure employment-truth rules for people, employment versions, positions, and assignments.

Use this package to:

1. Reconstruct what was true on an effective date and what Orgmetra knew at a recorded instant.
2. Reject an assignment that is not covered by the worker's employment.
3. Reject an allocation portfolio that exceeds 1.0000 for one employment.
4. Close a recorded interval and insert a replacement instead of rewriting history.

This kernel does not talk to PostgreSQL, Keyverse, or any other service. Persistence and authorization stay at their adapter boundaries.
