# Changelog

## Unreleased

- Add a PII-minimized candidate-evidence intake packet with exact candidate/requisition/Job/job-requirements correlation.
- Bind evidence, source provenance, handling and retention artifacts by opaque reference and SHA-256 digest.
- Require bounded evidence counts, fixed purpose, explicit human-review state, precision-preserving UTC timestamps, deterministic canonical JSON, and exact packet SHA-256.
- Keep raw candidate evidence, demographic attributes, assessment values, credentials, and free-form model output outside the governance packet.
