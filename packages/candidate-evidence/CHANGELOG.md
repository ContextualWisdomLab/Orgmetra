# Changelog

## Unreleased

- Add a PII-minimized candidate-evidence intake packet with exact candidate/requisition/Job/job-requirements correlation.
- Bind evidence, source provenance, handling and retention artifacts by UUID-backed opaque reference and SHA-256 digest.
- Reject human-readable/value-bearing reference suffixes and sentinel/noncanonical UUIDs so governance references cannot become a covert candidate-data channel.
- Require every packet reference to be re-resolved within the exact tenant through its authoritative boundary before candidate↔requisition↔Job correlation, evidence sealing, or accountable review, preventing cross-tenant evidence mixing behind valid UUIDs.
- Redact the ordinary packet representation so candidate correlation and evidence digests are not emitted through routine logs/assertion failures.
- Require bounded evidence counts, fixed purpose, explicit human-review state, precision-preserving UTC timestamps, deterministic canonical JSON, and exact packet SHA-256.
- Keep raw candidate evidence, demographic attributes, assessment values, credentials, and free-form model output outside the governance packet.
