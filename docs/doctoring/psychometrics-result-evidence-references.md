# Psychometrics result evidence references

Reviewed: 2026-08-23 (Asia/Seoul).

## APA 7 references

American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*. American Educational Research Association. https://www.testingstandards.net/open-access-files.html

ContextualWisdomLab. (2026). *ADR-0010: Versioned provenance and immutable results* [Software documentation]. GitHub. https://github.com/ContextualWisdomLab/psychometrics-commons/blob/3bb873f02d2e1639be49e2bc9ac998c158b48d3d/docs/adr/0010-versioned-provenance-and-immutable-results.md

ContextualWisdomLab. (2026). *Internal normalization for opaque product references* [Source code]. GitHub. https://github.com/ContextualWisdomLab/psychometrics-commons/blob/3bb873f02d2e1639be49e2bc9ac998c158b48d3d/src/reference.rs

ContextualWisdomLab. (2026). *Immutable product result snapshots and supersession provenance* [Source code]. GitHub. https://github.com/ContextualWisdomLab/psychometrics-commons/blob/3bb873f02d2e1639be49e2bc9ac998c158b48d3d/src/result.rs

ContextualWisdomLab. (2026). *Scoring-dispatch contracts that pin immutable measurement provenance* [Source code]. GitHub. https://github.com/ContextualWisdomLab/psychometrics-commons/blob/3bb873f02d2e1639be49e2bc9ac998c158b48d3d/src/scoring.rs

## Review notes

The Testing Standards site still publishes the 2014 English edition as the current final edition. The sponsoring organizations announced a revision committee in 2024, so this record does not describe the revision-in-progress as a final standard.

Psychometrics Commons protected `main` was read-only reviewed at exact revision `3bb873f02d2e1639be49e2bc9ac998c158b48d3d`. Its accepted ADR-0010 requires immutable versioned provenance and treats digest mismatch as fatal. The current scoring implementation requires `engine_artifact_digest` in canonical `sha256:<64 lowercase hexadecimal>` form. The current `ResultSnapshot` copies result provenance and score observations from validated scoring state rather than recomputing psychometric values product-side.

The pinned owner's `normalized_reference` trims references and rejects blank, numeric-like, or Unicode control-character values, but it does not reject all Unicode `C*` categories. Orgmetra therefore requires foreign references to arrive already normalized, preserves the owner's numeric/control-character rule, and does not reject owner-valid Unicode format characters merely because Python classifies them as `Cf`. Orgmetra retains a local 256-character transport bound without changing the foreign identifier format.

Orgmetra intentionally binds the result and provenance while storing only digests for the foreign participant binding and consent-reference set. This is a data-minimization choice at the HR governance boundary, not a modification of the Psychometrics Commons owner contract.
