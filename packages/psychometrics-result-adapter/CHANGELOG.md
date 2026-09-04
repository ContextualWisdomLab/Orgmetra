# Changelog

## Unreleased

- Add an Orgmetra-owned, value-minimized evidence envelope for immutable Psychometrics Commons result provenance.
- Pin the reviewed dependency contract to `psychometrics-commons@3bb873f02d2e1639be49e2bc9ac998c158b48d3d` without mutating the dependency.
- Keep raw participant identifiers, score observations, standard errors, consent references, credentials, and HR PII out of canonical evidence.
- Require independent requester/reviewer correlations, exact owner schema version, canonical SHA-256 provenance, source-result chronology, and fail-closed supersession integrity.
- Preserve opaque references that satisfy the pinned owner's normalization contract, including owner-valid Unicode format characters, while retaining Orgmetra's local length bound and the owner's numeric/control-character rejection rules.
- Prevent the envelope itself from granting high-impact employment-decision authority.
- Return the exact payload and JSON snapshot whose creation seal was verified so canonical export cannot diverge through a second live-field read.
- Run installed-wheel tests in a fully isolated virtual environment whose pytest/coverage toolchain is installed from the repository's reviewed hash-pinned dependency set; fail closed if the adapter or those test dependencies resolve outside that environment.
