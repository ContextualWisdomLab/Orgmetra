# Orgmetra Psychometrics Result Adapter

This package records **governed evidence that a reviewed Psychometrics Commons result exists**. It does not calculate scores, copy a foreign participant identifier into Orgmetra audit evidence, or authorize a hiring, promotion, compensation, termination, or other employment decision.

## What the envelope binds

`PsychometricsResultEvidenceEnvelope` binds one Orgmetra tenant and the protected-main `candidate_evidence_intake:<UUIDv4>` packet plus its canonical SHA-256 digest to an immutable Psychometrics Commons result snapshot. It preserves the owner's result/provenance references for response snapshot, assessment specification, instrument, scoring, calibration, optional norm, narrative, engine artifact, schema version, creation time, and optional supersession. It also records SHA-256 evidence for the authorized participant binding, consent-reference set, and exact result snapshot bytes.

The reviewed owner revision is `ContextualWisdomLab/psychometrics-commons@3bb873f02d2e1639be49e2bc9ac998c158b48d3d`. The adapter deliberately accepts the owner's already-normalized opaque references rather than inventing a UUID format for foreign identifiers. Orgmetra-owned result/intake/actor correlations remain bounded UUID-based references.

## Privacy and decision authority

The durable canonical document omits raw `participant_ref`, score observations, standard errors, consent references, prompts, credentials, and HR PII. A purpose-authorized integration layer must compute `participant_binding_digest` before the raw foreign participant identifier is discarded from this evidence boundary.

Every envelope remains:

- `external_measurement_evidence`;
- `requires_human_review`;
- `score_values_not_stored`; and
- `not_authorized_for_employment_decision`.

A downstream high-impact HR action must re-resolve the candidate/worker through the bound candidate-evidence intake, purpose, evidence versions, result scope, and human decision authority at its own authoritative boundary. This packet is evidence, not approval.

## Integrity and chronology

The adapter rejects malformed or identifying actor correlations, a candidate-intake reference/digest that does not satisfy the protected-main intake contract shape, noncanonical foreign references, digest drift, an unsupported owner output-schema version, self-supersession, and a source result whose creation time is later than Orgmetra's system-recorded evidence time. Canonical output is deterministically serialized and guarded against post-construction rewriting by process-local creation evidence; durable persistence must still rely on Orgmetra's immutable audit/outbox and database controls rather than treating the in-process seal as a storage signature.

## Ownership boundary

Psychometrics Commons owns assessment sessions, scoring, psychometric computation, result snapshots, and their scientific provenance. Orgmetra consumes only published package/API/event/export contracts. It never reads or writes the Psychometrics Commons application database directly.

## Next action for an operator

If a result cannot be bound, do not copy a score or participant identifier around the contract. Verify the exact candidate-evidence intake reference and digest, Psychometrics Commons revision and result snapshot, re-establish the authorized candidate-to-participant binding, and obtain a human reviewer before the evidence is used by any Orgmetra decision workflow.
