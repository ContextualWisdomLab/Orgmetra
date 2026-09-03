# Changelog

## Unreleased

- Add a PII-minimized candidate-evidence intake packet with exact candidate/requisition/Job/job-requirements correlation.
- Follow Orgmetra's authoritative canonical non-sentinel operational UUID contract for `tenant_record_id`, while packet-owned evidence, source-provenance, handling and retention references remain canonical UUIDv4-backed opaque identity; content-bearing evidence also carries SHA-256 digests.
- Reject human-readable/value-bearing reference suffixes, sentinel/noncanonical reference UUIDs, and UUIDv1/non-v4 packet-reference suffixes so trust-reference fields cannot become a covert candidate-data or correlation channel without duplicating tenant identity policy.
- Require every packet reference to be re-resolved within the exact tenant through its authoritative boundary before candidate↔requisition↔Job correlation, evidence sealing, or accountable review, preventing cross-tenant evidence mixing behind valid UUID syntax.
- Redact the ordinary packet representation so candidate correlation and evidence digests are not emitted through routine logs/assertion failures.
- Reject `str` subclasses at every digest boundary so canonical evidence retains only exact immutable text.
- Normalize UTC conversion overflow at the collection-time boundary into the packet's fail-closed validation error.
- Require bounded evidence counts, fixed purpose, explicit human-review state, precision-preserving UTC timestamps, deterministic canonical JSON, and exact packet SHA-256.
- Keep raw candidate evidence, demographic attributes, assessment values, credentials, and free-form model output outside the governance packet.
