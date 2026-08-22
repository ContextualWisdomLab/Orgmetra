# Release-candidate evidence primary references

## Scope

These references support the active release-candidate evidence design. They are technical design inputs, not certification, conformance-attestation, SLSA-level, or legal-compliance claims.

## APA 7 references

OWASP Foundation. (2025, October 21). *CycloneDX specification overview (Version 1.7)*. CycloneDX. https://cyclonedx.org/specification/overview/

OWASP Foundation. (2025). *CycloneDX v1.7 JSON reference*. CycloneDX. https://cyclonedx.org/docs/1.7/json/

Supply-chain Levels for Software Artifacts. (2026). *SLSA specification (Version 1.2)*. Linux Foundation. https://slsa.dev/spec/v1.2/

Supply-chain Levels for Software Artifacts. (2026). *Build: Provenance (Version 1.2)*. Linux Foundation. https://slsa.dev/spec/v1.2/build-provenance

in-toto Project. (2026). *Statement layer specification (in-toto Attestation Framework v1)*. https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md

in-toto Project. (2026). *Envelope layer specification (in-toto Attestation Framework v1)*. https://github.com/in-toto/attestation/blob/main/spec/v1/envelope.md

## Design consequences

- CycloneDX 1.7 is used because it is the current stable CycloneDX specification; the announced 2.0 work remains future/draft material and is not used as a release gate.
- The SBOM uses the required CycloneDX format/version identifiers and deterministic, unique `bom-ref` values. It records exact versions only when checked-in package metadata declares an exact version; dependency ranges are not promoted into fabricated resolved versions.
- The provenance document uses in-toto Statement v1 and the SLSA-required predicate identifier `https://slsa.dev/provenance/v1`. It records the exact source revision as a resolved Git dependency and binds output SHA-256 digests.
- SLSA v1.2 makes builder trust and provenance-generation accuracy part of the build-platform trust boundary. Because this repository-owned script generates an unsigned Statement inside the workload, Orgmetra does not infer a SLSA Build level or authenticated provenance from this evidence alone.
- The in-toto envelope layer treats authentication/signatures as a separate outer layer. This slice therefore stops at deterministic unsigned candidate evidence and leaves trusted signing/attestation to a later protected release boundary.
