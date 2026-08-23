# Orgmetra document-record evidence

This package creates **value-minimized metadata evidence** for an HR document artifact. It is intended for the `document_records` bounded context described by Orgmetra's accepted architecture.

A `DocumentRecordEvidence` binds one tenant, Person, Employment, uploader correlation, reviewed document category, immutable artifact reference and SHA-256 digest, source-provenance digest, retention-policy reference/digest, the business receipt time, and a system-generated recorded time. The evidence intentionally contains **no document bytes, document title, free-form notes, credentials, compensation, rating, or other HR field values**.

The packet is not a storage credential, legal retention determination, or employment-decision authorization. Before content access, export, retention/disposition, or a high-impact HR action, the authoritative Orgmetra host must re-resolve tenant/actor/purpose/resource scope, retention/legal-hold state, artifact integrity and human authority, then persist immutable audit/outbox evidence through the owning service.

`document_record_reference` and `recorded_at` are generated inside the Orgmetra issuance boundary so callers cannot claim a chosen system-recorded identity or timestamp. Caller-owned `received_at` remains separate business-event time and must be exact built-in UTC and no later than issuance.

The closed initial document-category vocabulary is `employment_contract`, `policy_acknowledgement`, and `qualification_document`. New categories require a reviewed contract change rather than free-form metadata.

This package does not fetch or mutate Clearfolio, NewsDOM, or any other dedicated-writer CWL service and introduces no cross-service application-table SQL.
