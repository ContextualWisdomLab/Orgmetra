# Changelog

## Unreleased

- Add an Orgmetra-owned, value-minimized evidence envelope for immutable Psychometrics Commons result provenance.
- Pin the reviewed dependency contract to `psychometrics-commons@3bb873f02d2e1639be49e2bc9ac998c158b48d3d` without mutating the dependency.
- Keep raw participant identifiers, score observations, standard errors, consent references, credentials, and HR PII out of canonical evidence.
- Require independent requester/reviewer correlations, exact owner schema version, canonical SHA-256 provenance, source-result chronology, and fail-closed supersession integrity.
- Prevent the envelope itself from granting high-impact employment-decision authority.
