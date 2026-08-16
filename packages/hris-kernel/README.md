# Orgmetra HRIS kernel

Pure employment-truth rules for people, employment versions, positions, and assignments.

Use this package to:

1. Reconstruct what was true on an effective date and what Orgmetra knew at a recorded instant.
2. Reject an assignment that is not covered by the worker's employment or a staffable position.
3. Reject two exclusive jobs that share days, or a seat whose visible allocations exceed 1.0000.
4. Reject an allocation portfolio that exceeds 1.0000 for one employment.
5. Close a recorded interval and insert a replacement instead of rewriting history.

This kernel does not talk to PostgreSQL, Keyverse, or any other service. Persistence and authorization stay at their adapter boundaries.
