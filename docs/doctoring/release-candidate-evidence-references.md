# Release-candidate evidence primary references

## Scope

These references support the active release-candidate evidence design. They are technical design inputs, not certification, conformance-attestation, SLSA-level, or legal-compliance claims.

## APA 7 references

Deutsch, L. P. (1996a). *DEFLATE compressed data format specification version 1.3* (RFC 1951). RFC Editor. https://doi.org/10.17487/RFC1951

Deutsch, L. P. (1996b). *GZIP file format specification version 4.3* (RFC 1952). RFC Editor. https://doi.org/10.17487/RFC1952

OWASP Foundation. (2025, October 21). *CycloneDX specification overview (Version 1.7)*. CycloneDX. https://cyclonedx.org/specification/overview/

OWASP Foundation. (2025). *CycloneDX v1.7 JSON reference*. CycloneDX. https://cyclonedx.org/docs/1.7/json/

Python Packaging Authority. (2026, August 19). *Version specifiers*. Python Packaging User Guide. https://packaging.python.org/en/latest/specifications/version-specifiers/

Supply-chain Levels for Software Artifacts. (2026). *SLSA specification (Version 1.2)*. Linux Foundation. https://slsa.dev/spec/v1.2/

Supply-chain Levels for Software Artifacts. (2026). *Build: Provenance (Version 1.2)*. Linux Foundation. https://slsa.dev/spec/v1.2/build-provenance

in-toto Project. (2026). *Statement layer specification (in-toto Attestation Framework v1)*. https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md

in-toto Project. (2026). *Envelope layer specification (in-toto Attestation Framework v1)*. https://github.com/in-toto/attestation/blob/main/spec/v1/envelope.md

## Design consequences

- RFC 1952 defines the gzip member header/trailer and CRC-32 integrity field; RFC 1951 permits non-compressed `BTYPE=00` DEFLATE blocks with 16-bit `LEN`/one's-complement `NLEN`. Orgmetra uses that standards-defined stored-block form for `orgmetra-stored-gzip-v1`, avoiding host-zlib-dependent evidence bytes while remaining readable by standard gzip implementations. The trade-off is intentionally larger source archives in exchange for reproducibility.
- CycloneDX 1.7 is used because it is the current stable CycloneDX specification; the announced 2.0 work remains future/draft material and is not used as a release gate.
- The SBOM uses the required CycloneDX format/version identifiers and deterministic, unique `bom-ref` values. It records exact versions only when checked-in package metadata declares an unconditional concrete version; non-exact or environment-marker-bearing Python/npm declarations keep the original declaration and use a stable digest-derived identity so ranges or markers are not conflated.
- The Python dependency parser follows the PyPA version-specifier normalization rules for concrete PEP 440 versions rather than recognizing only canonical spellings. Accepted aliases and separators such as `v1.2`, `1.0-preview1`, `1.0_rev_1`, and implicit post-release `1.0-1` normalize to canonical evidence identities, while `==1.*`, compound clauses, arbitrary equality, and environment-marker-bearing declarations remain declaration evidence rather than unconditional package identities.
- The provenance document uses in-toto Statement v1 and the SLSA-required predicate identifier `https://slsa.dev/provenance/v1`. It records the exact source revision as a resolved Git dependency and binds output SHA-256 digests.
- SLSA v1.2 makes `builder.id` the identity of the build platform/trust boundary and requires differing operating modes with differing security properties to use distinct identities. Orgmetra therefore distinguishes GitHub Actions execution from local execution rather than labeling locally generated candidate provenance as GitHub Actions evidence.
- SLSA v1.2 also makes builder trust and provenance-generation accuracy part of the build-platform trust boundary. Because this repository-owned script generates an unsigned Statement inside the workload, Orgmetra does not infer a SLSA Build level or authenticated provenance from this evidence alone.
- The in-toto envelope layer treats authentication/signatures as a separate outer layer. This slice therefore stops at deterministic unsigned candidate evidence and leaves trusted signing/attestation to a later protected release boundary.