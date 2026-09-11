# Document-record evidence references

Reviewed 2026-08-23.

## Primary standards inputs

World Wide Web Consortium. (2013, April 30). *PROV-O: The PROV Ontology* (W3C Recommendation). https://www.w3.org/TR/prov-o/

PROV-O is used as a provenance-model design input: Orgmetra preserves explicit artifact and source-provenance correlation so evidence can later be mapped into a broader provenance graph. This slice does **not** claim PROV-O serialization conformance.

National Institute of Standards and Technology. (2020, January). *NIST Privacy Framework: A tool for improving privacy through enterprise risk management, Version 1.0*. https://www.nist.gov/privacy-framework/privacy-framework

NIST Privacy Framework 1.0 is used as a privacy-risk design input for data minimization and governed processing. At the review date, NIST's site separately presents Privacy Framework 1.1 as an Initial Public Draft; this document therefore does not mislabel 1.1 as a final standard and does not claim NIST certification or conformity.

## Orgmetra interpretation

The evidence contract stores document metadata, opaque correlations and SHA-256 provenance while excluding document bytes, titles, free-form notes, credentials and unrelated HR values. Retention-policy evidence is bound but no universal statutory retention period is encoded. Authoritative access, export, retention/disposition and employment decisions remain separate human-accountable Orgmetra boundaries.
