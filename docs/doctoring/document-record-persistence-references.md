# Document-record persistence references

## Status

Primary-source design references reviewed for the active document-record persistence PR on 2026-08-24. These sources inform the design; Orgmetra does not claim standards certification or conformance from their citation.

## APA 7 references

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: CREATE POLICY*. https://www.postgresql.org/docs/16/sql-createpolicy.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: ALTER TABLE*. https://www.postgresql.org/docs/16/sql-altertable.html

World Wide Web Consortium. (2013, April 30). *PROV-O: The PROV ontology* (W3C Recommendation). https://www.w3.org/TR/prov-o/

## Design use

PostgreSQL `CREATE POLICY` documents that row visibility and new-row checks are controlled by `USING` and `WITH CHECK` once row-level security is enabled; false or null policy results do not expose rows. `ALTER TABLE ... FORCE ROW LEVEL SECURITY` additionally applies row policies to the table owner, so this PR uses both ENABLE and FORCE and still tests a NOSUPERUSER/NOBYPASSRLS reader.

PROV-O is used only as a provenance design reference: the persisted relation carries source-provenance and evidence correlations without copying source document content. The repository's own service-ownership contract remains authoritative for direct-database-access boundaries.
