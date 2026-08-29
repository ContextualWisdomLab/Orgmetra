# Changelog

## Unreleased

- Add a non-executing, fail-closed Orgmetra binding for TEPP `AnalysisRunRequest` contract v1, pinned to reviewed TEPP protected revision `7c29e7c971d7940e1fb3def1ed3aae2d1bc8ad4a`.
- Bind workforce-validation study/actor provenance, immutable snapshot digest, RFC 3339 cutoff, evidence version, exact request digest, and same-key retry/conflict semantics without copying source text, credentials, or direct identity values into the TEPP request.
- Reject common credential-shaped values in both TEPP foreign opaque identifiers and the idempotency key so the packet cannot persist or forward an obvious secret while asserting that credentials are absent.
- Align `tenant_record_id` with protected Orgmetra's canonical non-sentinel operational UUID contract, including UUIDv7 interoperability, while keeping packet-owned validation-study and actor references UUIDv4-constrained.
- Detach timezone-aware `knowledge_cutoff` and `generated_at` values to exact UTC datetimes before canonical request and governance evidence, rejecting failing, malformed, or overflowing timezone providers.
- Keep transport disabled until a compatible executable TEPP service contract is published and re-resolved by the host; returned analytical/LLM evidence remains human-scientific-review-only.
- Make `TEPP Adapter Quality` retrigger on shared repository Python/test/clean-checkout configuration, with an executable regression preventing stale adapter-quality evidence after shared tooling changes.
