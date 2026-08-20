# Changelog

## Unreleased

- Add a PII-minimized candidate-evidence intake packet with exact candidate/requisition/Job/job-requirements correlation.
- Bind the public tenant identity plus evidence, source provenance, handling and retention artifacts to canonical UUIDv4-backed opaque identity; content-bearing evidence also carries SHA-256 digests.
- Reject human-readable/value-bearing reference suffixes, sentinel/noncanonical UUIDs, UUIDv1 timestamp/node correlation metadata, and every other non-v4 UUID version so tenant/reference identities cannot become a covert candidate-data or correlation channel.
- Require every packet reference to be re-resolved within the exact tenant through its authoritative boundary before candidate↔requisition↔Job correlation, evidence sealing, or accountable review, preventing cross-tenant evidence mixing behind valid UUIDv4 syntax.
- Redact the ordinary packet representation so candidate correlation and evidence digests are not emitted through routine logs/assertion failures.
- Require bounded evidence counts, fixed purpose, explicit human-review state, precision-preserving UTC timestamps, deterministic canonical JSON, and exact packet SHA-256.
- Keep raw candidate evidence, demographic attributes, assessment values, credentials, and free-form model output outside the governance packet.