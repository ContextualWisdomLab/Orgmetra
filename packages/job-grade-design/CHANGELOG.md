# Changelog

## 0.1.0 - Unreleased

- Add a PII-minimized `JobGradeDesignReviewPacket` that binds an authoritative Job and persisted Job Analysis snapshot to a reviewed enterprise-local Job-evaluation method, proposed grade/band codes, architecture-definition digest, separated accountable actors, explicit canonical evidence schema version, and distinct human-review/system-recorded times.
- Keep every packet explicitly non-authoritative for grade assignment, compensation, Position/Assignment mutation, and employment decisions.
- Require exact built-in `evidence_version = 1` in canonical evidence so a durable review cannot omit or caller-inflate the schema version; unsupported/coercible versions fail closed.
- Reject reserved identifier sentinels, hostile runtime subclasses, noncanonical evidence digests/codes, non-UUIDv4 packet-owned actor references, non-UTC evidence time, reviewer/requester overlap, and system recording before human review.
- Seal creation-time canonical evidence outside packet-writable slots so post-issuance mutation fails closed while keeping durable authorization/persistence ownership outside this process-local defense.
- Add exact-head CI with exact 100% owned production statement/branch coverage and clean-checkout enforcement.
