# ADR: Governed Psychometrics Commons result evidence

## Status

Accepted on active PR #85 only. This is not protected-main truth until the exact integrated head is merged.

## Context

Orgmetra needs assessment evidence in candidate and workforce decision workflows, but Psychometrics Commons is the dedicated owner of assessment sessions, scoring, immutable result snapshots, and psychometric computation. Direct table access or copying that numerical kernel into Orgmetra would violate the federated CWL boundary in ADR 0002.

Fresh read-only review of `ContextualWisdomLab/psychometrics-commons@3bb873f02d2e1639be49e2bc9ac998c158b48d3d` found that accepted owner ADR-0010 requires immutable versioned result provenance. Its `ResultSnapshot` binds response/assessment/instrument/scoring/calibration/norm/narrative/consent/engine provenance, creation time, and optional supersession, while the owner runtime explicitly does not recompute psychometric values when publishing the result.

Protected Orgmetra `develop` already defines candidate-evidence intake through `candidate_evidence_intake:<UUIDv4>` plus deterministic packet evidence. The psychometrics adapter must bind to that existing canonical intake boundary rather than inventing a parallel candidate-evidence identifier.

The current 2014 *Standards for Educational and Psychological Testing* remains the final published edition while a revision process is underway. Its testing-governance framework reinforces that score interpretation and use require validity evidence and appropriate controls rather than treating a numerical output as self-authorizing.

## Decision

Orgmetra will consume Psychometrics Commons result evidence through a dedicated adapter and will not query or mutate the foreign application database.

The Orgmetra envelope binds:

- one tenant plus the protected-main `candidate_evidence_intake:<UUIDv4>` reference and its canonical SHA-256 digest;
- distinct pseudonymous requesting and reviewing actor correlations;
- the foreign immutable result snapshot and its response, assessment, instrument, scoring, calibration, optional norm, narrative, output-schema, engine-artifact, creation-time, and optional supersession provenance;
- SHA-256 evidence for the authorized candidate-to-foreign-participant binding, consent-reference set, and exact result snapshot bytes; and
- the exact reviewed Psychometrics Commons source revision.

The envelope does **not** copy raw foreign participant identifiers, score observations, standard errors, consent references, credentials, or HR PII. Foreign opaque references remain foreign-owned and are validated only for canonical safe representation; Orgmetra does not invent UUID semantics for them.

Every envelope is explicitly `external_measurement_evidence`, `requires_human_review`, `score_values_not_stored`, and `not_authorized_for_employment_decision`. Any hiring or other high-impact HR action must re-resolve authoritative identity through the bound candidate intake, purpose, evidence version, job/decision scope, and human authority at the owning Orgmetra decision boundary.

## Integrity rules

- The candidate-evidence intake reference/digest must match Orgmetra's protected-main candidate-intake contract shape; this adapter does not create a second candidate identity.
- Owner revision and supported output-schema version are pinned before evidence acceptance.
- The owner-published engine artifact must use its canonical `sha256:<64 lowercase hex>` format.
- Result evidence cannot claim that Orgmetra recorded it before the owner's result creation timestamp.
- A result cannot supersede itself.
- Canonical evidence is deterministically serialized from the exact payload snapshot whose creation seal was verified, and detects post-construction rewriting in-process. Durable immutability still belongs to Orgmetra audit/outbox and persistence controls; the in-process seal is not represented as a storage signature.
- Exact built-in runtime primitives are required at trust-bearing Python boundaries to prevent caller-defined equality, hashing, comparison, or serialization behavior from changing validated meaning.

## Consequences

Orgmetra can correlate a reviewed assessment result with an already-governed candidate-evidence intake and later validation studies without becoming a psychometric engine or persisting unnecessary score/participant payload in governance evidence. Buyers receive reproducible provenance and a clear human-review step; specialist ownership and standalone deployment remain intact.

## References

See `docs/doctoring/psychometrics-result-evidence-references.md` for the APA 7 reference record and exact dependency revision reviewed for this decision.
