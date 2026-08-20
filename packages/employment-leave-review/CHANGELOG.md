# Changelog

## Unreleased

- Added a governed, value-minimized employment-leave review packet with authoritative tenant/worker-scope resolution, exact leave-case/policy provenance, work/benefits continuity and return-to-work evidence, human-only approval, and fail-closed mutation/external-execution states.
- Required canonical non-sentinel UUIDv4 identity for `tenant_record_id` and every namespaced trust reference, rejecting UUIDv1 timestamp/node correlation metadata and every other UUID version.
- Excluded direct identifiers, medical/family values, compensation/benefit values, and free-form leave-reason narrative from the portable governance envelope; only non-sensitive workflow reason categories are permitted.
- Classified the opaque worker correlation plus exact requested leave dates honestly as minimum-necessary personal data (`contains_person_pii=true`) instead of misrepresenting data minimization as PII-free evidence.
- Bound exact personal-data handling-policy and retention-policy references/digests into canonical evidence so a privacy-governance version change changes the packet SHA-256; policy binding remains evidence of the reviewed contract, not proof of enforcement.
