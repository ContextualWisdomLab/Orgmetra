# Governed migration handoff references

## Status

Active-PR evidence only. Protected `develop` does not ship this migration handoff until the owning PR integrates.

## Exact dependency contracts

- ContextualWisdomLab. (2026). *MHTML ETL Gateway API contract* [Source code, revision `779254927abb1e7cee80fd949907ccd03f9fc7be`]. GitHub. The reviewed `0.4.0` API exposes source SHA-256 identity and value-free schema/handoff contracts without database writes, network transport, authentication, or raw source values.
- ContextualWisdomLab. (2026). *MHTML ETL Gateway value-free schema proposal contract* [Source code, revision `779254927abb1e7cee80fd949907ccd03f9fc7be`]. GitHub. The reviewed proposal contract exposes `schema_proposal_id`, `source_hash_sha256`, and `table_fingerprint_sha256` while excluding raw headers and values.
- ContextualWisdomLab. (2026). *mightyETL bounded atomic batch contract* [Source code, revision `ba8911f50ed20a39927a0d51c0cf20f9b7c91820`]. GitHub. The reviewed contract prevalidates one bounded request before database writes and executes accepted writes inside one transaction; Orgmetra does not copy or extend its runtime semantics in this slice.

## Authoritative standards

- World Wide Web Consortium. (2013, April 30). *PROV-DM: The PROV data model* (W3C Recommendation). https://www.w3.org/TR/prov-dm/
- National Institute of Standards and Technology. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53, Revision 5). https://doi.org/10.6028/NIST.SP.800-53r5

NIST's current CSRC publication page records a Release 5.2.0 update notice dated August 27, 2025. Orgmetra uses the public information-integrity and provenance principles as design traceability only and does not claim NIST, ISO, SOC 2, or other certification from this package.
