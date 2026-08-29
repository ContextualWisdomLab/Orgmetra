# Changelog

## Unreleased

- Added a governed, value-free employment-separation review packet with exact evidence binding, controlled non-sensitive reason metadata, authoritative-scope resolution, human-only approval, and fail-closed mutation/external-execution states.
- Required canonical non-sentinel UUIDv4 identity for every packet-owned namespaced trust reference, rejecting UUIDv1 timestamp/node correlation metadata and every other UUID version.
- Strengthened authoritative-scope review so every packet reference must be re-resolved inside the exact tenant context and the Person-to-Employment plus active Assignment/Job/Position worker binding must be proven before approval.
- Changed `tenant_record_id` to follow protected Orgmetra's authoritative canonical non-sentinel operational-UUID contract, accepting the core UUIDv7 tenant form while retaining RFC 9562 Nil/Max rejection.
- Freeze `generated_at` to a detached built-in UTC instant at issuance, reject future system-recorded instants, normalize missing/raising/overflowing timezone providers to fail-closed validation, and prevent caller-owned timezone behavior from rewriting canonical separation evidence after issuance.
- Seal each live review packet's exact canonical bytes in process-local evidence outside packet-writable slots, so valid-to-valid post-construction rewriting or loss of issuance evidence fails closed before canonical audit correlation or downstream approval can use the packet. This is defense-in-depth only; durable systems still own persisted uniqueness and immutable audit/outbox evidence.
- Make `Employment Separation Review Quality` retrigger on shared repository Python/test/clean-checkout configuration, with an executable regression that prevents package-quality evidence from remaining stale after shared tooling changes.
