# Changelog

## Unreleased

- Added a governed, value-minimized employment-leave review packet that validates references and fixed governance states while requiring the host authority to re-resolve tenant/worker scope before approval; exact leave-case/policy provenance, work/benefits continuity and return-to-work evidence, human-only approval, and fail-closed mutation/external-execution states.
- Required canonical non-sentinel UUIDv4 identity for every packet-owned namespaced trust reference, rejecting UUIDv1 timestamp/node correlation metadata and every other UUID version.
- Changed `tenant_record_id` to follow protected Orgmetra's authoritative canonical non-sentinel operational-UUID contract, accepting the core UUIDv7 tenant form while retaining RFC 9562 Nil/Max rejection.
- Excluded direct identifiers, medical/family values, compensation/benefit values, and free-form leave-reason narrative from the portable governance envelope; only non-sensitive workflow reason categories are permitted.
- Classified the opaque worker correlation plus exact requested leave dates honestly as minimum-necessary personal data (`contains_person_pii=true`) instead of misrepresenting data minimization as PII-free evidence.
- Bound exact personal-data handling-policy and retention-policy references/digests into canonical evidence so a privacy-governance version change changes the packet SHA-256; policy binding remains evidence of the reviewed contract, not proof of enforcement.
- Bound each live packet instance to its creation-time canonical evidence digest so low-level post-construction field rewriting cannot emit a second valid-looking truth; unsupported copied instances fail closed, while `dataclasses.replace(...)` remains an explicit newly validated packet issuance rather than a mutation of the original object.
- Consolidated Employment Leave Review package quality under the protected canonical Foundation workflow: the retired package-local workflow stays deleted, the package is built as an exact-checkout wheel and installed by computed SHA-256 into an isolated environment, and its owned production remains subject to exact 100% statement/branch coverage without package-local `PYTHONPATH` execution.
