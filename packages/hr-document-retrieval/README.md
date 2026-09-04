# Orgmetra HR Document Retrieval

`orgmetra-hr-document-retrieval` is the execution boundary for an authorized internal HR document read. It is intentionally separate from document metadata evidence, durable document-record persistence, export review, retention/disposition, and employment-decision logic.

A document identifier, cached UI row, review packet, or storage reference is never sufficient authority to release bytes. `retrieve_hr_document(...)` performs this sequence on every request:

1. validate all injected host capabilities before protected resolution;
2. snapshot and revalidate the exact tenant/document/requester/purpose/reason/byte-limit request;
3. resolve fresh authoritative document metadata;
4. obtain human-accountable authorization bound to the exact tenant, document, Person, Employment, artifact reference and digest, retention state, classification, purpose, reason, requester, delivery context, and byte limit;
5. perform a bounded artifact read and verify SHA-256 against both storage output and authoritative metadata;
6. recheck authorization freshness against the just-verified artifact;
7. append a value-minimized immutable retrieval receipt; and
8. recheck authorization freshness after the audit append and immediately before release; and
9. only then return the bytes.

The result is always `not_authorized_for_employment_decision`. This package does not evaluate the document, infer suitability, classify a worker, or authorize hiring, termination, pay, performance, or any other high-impact employment action.

## Privacy and authorization boundary

The retrieval receipt records only bounded correlation and governance evidence: tenant/document/Person/Employment references, requester/reviewer correlations, purpose/reason, authorization-evidence digest, retention state, classification, media type, artifact SHA-256, byte count, delivery context, retrieval time, and fixed non-decision state. Document bytes, document text/title, free-form HR notes, compensation, assessment/rating values, credentials, tokens, and model output are never written to the receipt.

Authorization must be purpose-bound and exact-scope. The authorization result must independently match the freshly resolved artifact reference and digest, `restricted_hr` classification, current `retained_record` or `legal_hold_record` retention state, `authenticated_hr_session` delivery context, and the exact requested byte bound. Legal hold permits a reviewed read when policy allows; it does not grant disposition authority.

The artifact reader is a bounded storage port, not an authorization authority. The audit writer is expected to durably append immutable evidence or raise; an audit failure means no document bytes are released by this boundary.

## Integration ownership

This package exposes four injected host ports: fresh document metadata resolution, purpose-bound authorization, bounded artifact reading, and immutable audit append. It does not query foreign application tables or import active-PR-only implementations from other Orgmetra lanes.

Separate active Orgmetra PRs own document metadata evidence/persistence and export-review evidence. Their source, checks, reviews, and PR state do not transfer into this root slice. After integration, host composition may use their published contracts only when those contracts are actually present on the integrated default branch.

Deployment composition remains responsible for storage credentials, TLS, encryption at rest, bounded/streaming object-store reads, malware/content safety policy where applicable, retention/legal-hold resolution, and the customer-facing authenticated HR UI/API. External egress/download beyond the authenticated internal HR session is a separate export-execution decision and must not be inferred from this internal retrieval boundary.
