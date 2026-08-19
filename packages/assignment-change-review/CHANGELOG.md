# Changelog

## Unreleased

### Added

- Governed pre-mutation assignment-change review packet with exact opaque HRIS/evidence references, deterministic SHA-256 correlation, requester/reviewer separation, mandatory human review, and an explicit not-authorized-to-apply state.
- Exact workforce-allocation policy reference/digest binding alongside current-scope, allocation-plan, worker-impact, and communication evidence.
- Bounded positive `evidence_version` in canonical evidence so high-impact actor/purpose/reason evidence remains explicitly versioned.
- Tenant-scoped pre-approval re-resolution of every packet reference plus Person-to-Employment-to-current-Assignment and current worker-scope verification in the governed next action.
- Fail-closed prevention of Person PII, compensation values, free-form model output, noncanonical references, malformed evidence digests, free-form sensitive reason metadata, invalid evidence versions, and direct-construction governance bypasses.
