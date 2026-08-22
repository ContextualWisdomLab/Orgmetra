# Semantic Job Evidence — primary references

## Scope

These references support the active-PR decision to keep foreign ontology output as provenance-bearing source evidence that requires human review, rather than copying a dedicated-writer service or treating semantic resolution as authoritative Job/employment decision evidence. They also record the primary package metadata used to bind the adapter's declared Python support to its hosted compatibility evidence.

## References (APA 7)

ContextualWisdomLab. (2026). *Semantic Data Portal* (Revision e48aa13c4af7a4875d4b53e6a60b50405c265a2f) [Computer software]. GitHub. https://github.com/ContextualWisdomLab/semantic-data-portal/tree/e48aa13c4af7a4875d4b53e6a60b50405c265a2f

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV ontology* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/prov-o/

Python Software Foundation. (2026). *coverage 7.14.2 release metadata* [JSON metadata]. Python Package Index. https://pypi.org/pypi/coverage/7.14.2/json

Tabassi, E. (2023). *Artificial intelligence risk management framework (AI RMF 1.0)* (NIST AI 100-1). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.AI.100-1

## Evidence notes

- The pinned Semantic Data Portal README publishes `POST /ontology/resolve` as an ontology/terminology API. That is the exact foreign operation recorded by this Orgmetra adapter; the dependency remains read-only.
- W3C PROV-O is a W3C Recommendation for interoperable provenance representation across heterogeneous systems. The Orgmetra envelope uses a small application-specific provenance record rather than claiming PROV-O serialization compliance.
- NIST AI RMF 1.0 remains the published final framework while NIST develops revisions/profiles. Its risk-management framing supports keeping model/semantic outputs governed and reviewable. This package does not claim AI RMF conformity or certification.
- The official PyPI JSON for coverage 7.14.2 advertises Python 3.12, 3.13, and 3.14 support and publishes distinct SHA-256 digests for their CPython Linux wheels. The Orgmetra hash lock admits only the exact reviewed 3.12/3.13/3.14 coverage wheel hashes used by the hosted matrix; it does not disable `--require-hashes` or broaden dependency versions.
- No psychometric/statistical estimator is implemented in this slice, so no research-only statistical claim is introduced and no foreign psychometric kernel is duplicated.
