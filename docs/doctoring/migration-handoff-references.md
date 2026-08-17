# Governed migration handoff references

## Status

Active-PR evidence only. Protected `develop` does not ship this migration handoff until the owning PR integrates.

## Exact dependency contracts

- ContextualWisdomLab. (2026). *MHTML ETL Gateway API contract* [Source code]. `ContextualWisdomLab/mhtml-etl-gateway`, revision `779254927abb1e7cee80fd949907ccd03f9fc7be`. GitHub. https://github.com/ContextualWisdomLab/mhtml-etl-gateway/commit/779254927abb1e7cee80fd949907ccd03f9fc7be. The reviewed `0.4.0` API exposes source SHA-256 identity and value-free schema/handoff contracts without database writes, network transport, authentication, or raw source values.
- ContextualWisdomLab. (2026). *MHTML ETL Gateway value-free schema proposal contract* [Source code]. `ContextualWisdomLab/mhtml-etl-gateway`, revision `779254927abb1e7cee80fd949907ccd03f9fc7be`. GitHub. https://github.com/ContextualWisdomLab/mhtml-etl-gateway/commit/779254927abb1e7cee80fd949907ccd03f9fc7be. The reviewed proposal contract exposes `schema_proposal_id`, `source_hash_sha256`, and `table_fingerprint_sha256` while excluding raw headers and values.
- ContextualWisdomLab. (2026). *mightyETL bounded atomic batch contract* [Source code]. `ContextualWisdomLab/mightyETL`, revision `ba8911f50ed20a39927a0d51c0cf20f9b7c91820`. GitHub. https://github.com/ContextualWisdomLab/mightyETL/commit/ba8911f50ed20a39927a0d51c0cf20f9b7c91820. The reviewed contract prevalidates one bounded request before database writes and executes accepted writes inside one transaction; Orgmetra does not copy or extend its runtime semantics in this slice.

## Authoritative standards

- World Wide Web Consortium. (2013, April 30). *PROV-DM: The PROV data model* (W3C Recommendation). https://www.w3.org/TR/2013/REC-prov-dm-20130430/
- National Institute of Standards and Technology. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53, Revision 5). https://doi.org/10.6028/NIST.SP.800-53r5
- National Institute of Standards and Technology. (2025, August 27). *NIST releases revision to SP 800-53 security and privacy controls* (Release 5.2.0 notice). https://csrc.nist.gov/news/2025/nist-releases-revision-to-sp-800-53-controls

NIST's official CSRC publication page and release notice identify Release 5.2.0 as the finalized August 27, 2025 update. Orgmetra uses the public information-integrity and provenance principles as design traceability only and does not claim NIST, ISO, SOC 2, or other certification from this package.
