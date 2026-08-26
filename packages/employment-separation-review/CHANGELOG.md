# Changelog

## Unreleased

- Added an accountable `approve_employment_separation(...)` boundary that requires exact authoritative reviewer/scope verification and emits a value-minimized receipt that remains `not_authorized_to_apply` and `not_authorized_to_execute`.
- Bound approval to the exact pre-authority packet bytes/SHA-256 and approval instant, reject packet mutation or wrong-scope authority evidence, and protect live receipt canonical evidence with a process-local HMAC-backed issuance seal outside receipt-writable slots.
- Added a governed, value-free employment-separation review packet with exact evidence binding, controlled non-sensitive reason metadata, authoritative-scope resolution, human-only approval, and fail-closed mutation/external-execution states.
- Required canonical non-sentinel UUIDv4 identity for every packet-owned namespaced trust reference, rejecting UUIDv1 timestamp/node correlation metadata and every other UUID version.
- Strengthened authoritative-scope review so every packet reference must be re-resolved inside the exact tenant context and the Person-to-Employment plus active Assignment/Job/Position worker binding must be proven before approval.
- Changed `tenant_record_id` to follow protected Orgmetra's authoritative canonical non-sentinel operational-UUID contract, accepting the core UUIDv7 tenant form while retaining RFC 9562 Nil/Max rejection.
- Freeze `generated_at` to a detached built-in UTC instant at issuance, reject future system-recorded instants, normalize missing/raising/overflowing timezone providers to fail-closed validation, and prevent caller-owned timezone behavior from rewriting canonical separation evidence after issuance.
