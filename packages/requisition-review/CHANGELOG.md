# Changelog

## Unreleased

### Added

- `RequisitionReviewPacket` for PII-minimized, human-accountable requisition review evidence.
- Separate Job and optional Position references, with an exact Position restricted to one opening.
- Versioned job-requirements and headcount-authorization references without copying source-system payloads.
- Deterministic canonical JSON and SHA-256 correlation evidence.
- Exact 100% owned production statement and branch coverage requirement through Foundation CI.

### Security and privacy

- Require every trust-bearing namespaced reference to use a canonical non-sentinel UUID suffix so human-readable or value-bearing labels cannot enter portable evidence.
- Close `reason_code` to the reviewed non-sensitive `approved_growth_plan` value and restrict requirements versions to numeric `requirements_version_<positive-integer>` metadata.
- Redact `RequisitionReviewPacket` representation so routine logs and assertion failures do not disclose sensitive correlation references or evidence digests.
