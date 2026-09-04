# Orgmetra Semantic Job Evidence Adapter

This package is the Orgmetra-owned trust boundary for ontology-resolution evidence imported from the read-only Semantic Data Portal dependency.

## What it does

`SemanticJobEvidenceEnvelope` binds one ontology-resolution result to:

- one Orgmetra tenant and one opaque Job Analysis reference;
- one opaque ontology-request reference;
- distinct requesting and human-reviewing actors;
- the approved non-decision use `job_analysis_source_evidence`;
- SHA-256 digests of the submitted term evidence, returned response evidence, and reviewed source-catalog state;
- the reviewed Semantic Data Portal revision `e48aa13c4af7a4875d4b53e6a60b50405c265a2f`;
- the reviewed `POST /ontology/resolve` operation;
- an evidence version and exact UTC system-recorded timestamp.

The canonical document always declares the imported material to be `external_source_evidence`, `requires_human_review`, and `not_authorized_for_job_or_employment_decision`.

## What it deliberately does not do

The envelope does not carry the raw ontology query term, raw response, candidate/worker PII, credentials, scores, or a Job/employment decision. A syntactically valid actor reference is correlation evidence, not proof of identity. The host must resolve actors and tenant/Job Analysis scope through Orgmetra's authoritative boundaries before source evidence is accepted into a reviewed Job Analysis snapshot.

Orgmetra does not read Semantic Data Portal application tables. The foreign service remains independently deployable and is consumed only through its published API contract. A changed provider revision or API operation fails closed until reviewed and explicitly updated here.

## Evidence integrity

Trust-bearing text, integers, and timestamps must be exact built-in runtime types before equality, membership, bounds, UUID parsing, or serialization. Packet-owned references, including actor correlations, use canonical UUIDv4 suffixes; the tenant ID follows Orgmetra's canonical non-sentinel operational UUID contract. The envelope is final and detects post-construction rewriting before canonical evidence leaves the boundary. Its packet-owned HMAC is only a consistency value: the authoritative creation seal is held in a lock-protected process-local issuance registry outside envelope-writable slots, so rewriting both payload and packet seal still fails closed.

Canonical export returns the exact payload snapshot whose seal was verified; it does not re-read live fields after the integrity decision. This closes a same-process mutation window in which the checked bytes and emitted bytes could otherwise diverge.

The issuance registry and process seal key are intentionally process-local tamper evidence, not durable cryptographic attestation. Copy/deepcopy, pickle/unpickle, worker-process transfer, or process restart does not recreate issuance authority; a restored envelope fails closed. If durable evidence is needed, persist the already-emitted `canonical_json()` bytes and `evidence_digest()` in Orgmetra's immutable audit/outbox boundary rather than serializing the live envelope object. A future requirement for independent long-term envelope revalidation would need a separately governed managed/rotatable signing or MAC key boundary; this package does not claim one.

## Python compatibility

The package currently declares and tests Python `>=3.12,<3.15`. Hosted quality evidence runs the installed wheel and its reviewed test toolchain on Python 3.12, 3.13, and 3.14. A new Python minor must be added to the hosted compatibility matrix before the public support range is widened.

## Testing

The dedicated quality lane runs the package tests with exact 100% owned production statement and branch coverage and requires a clean checkout. Adversarial regressions cover malformed references/digests, self-review, runtime-subclass forgery, invalid dependency revision/API use, payload-only mutation, packet-seal mutation, payload plus recomputed-seal forgery, checked-snapshot export, replacement/seal reset, and runtime-type extension.

See `docs/traceability/semantic-job-evidence.md`, `docs/adr/semantic-job-source-evidence.md`, and `docs/doctoring/semantic-job-evidence-references.md` for the governed rationale and evidence map.
