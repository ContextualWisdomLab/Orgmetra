# ADR 0116: Purpose-bound HR document retrieval execution

- **Status:** Accepted for active PR; not protected-main truth until integrated
- **Date:** 2026-08-25
- **Owner:** Orgmetra `document_records` / HR authorization boundary

## Context

Orgmetra needs authorized HR staff to retrieve necessary document bytes without treating an identifier, login session, cached UI state, storage locator, or review packet as sufficient disclosure authority. Active Orgmetra lanes separately govern document metadata evidence/persistence and export review, but those PR-only contracts are not default-branch dependencies and their checks/reviews do not transfer here.

A defensible retrieval boundary must keep necessary PII usable for authorized HR work while preventing scope drift, confused-deputy reads, stale-retention reads, unaudited disclosure, and high-impact employment decisions from being inferred from document access.

## Decision

Implement one standalone transport-neutral execution boundary with four injected ports:

1. **Document metadata resolver** — freshly resolves the exact Orgmetra-owned tenant/document/Person/Employment/artifact/retention/classification scope.
2. **Document retrieval authority** — supplies human-accountable, purpose/reason-bound authorization for that exact fresh scope and byte limit.
3. **Artifact reader** — performs only the bounded read for the authorized artifact reference.
4. **Immutable audit writer** — durably appends a value-minimized canonical retrieval receipt before content can be returned.

Execution order is security-significant: capability validation → request snapshot → fresh metadata resolution → exact-scope authorization → bounded read → artifact SHA-256 verification → authorization freshness recheck → immutable audit append → final authorization freshness recheck → byte release.

Authorization is bound to tenant, document, Person, Employment, artifact reference/digest, current retention state, `restricted_hr` classification, requester/reviewer separation, purpose/reason, `authenticated_hr_session`, and exact byte bound. `retained_record` and `legal_hold_record` are eligible states; neither grants disposition authority. Denial, expiry, drift, malformed evidence, oversize, digest mismatch, or audit failure is fail-closed.

Canonical retrieval receipts exclude document bytes/text/title, free-form HR notes, compensation, assessment/rating values, credentials/tokens, and model output. The returned result is fixed to `not_authorized_for_employment_decision`.

## Consequences

- Necessary document content remains available to authorized HR workflows rather than being indiscriminately masked.
- Cached UI state and opaque references cannot authorize disclosure.
- Storage adapters cannot broaden policy scope; they receive only an exact artifact reference and byte limit after authorization.
- Audit persistence is part of the disclosure transaction boundary: if append fails, this API does not return document bytes.
- Internal authenticated retrieval does not itself authorize external export/download. External egress remains a separate governed execution boundary.
- This PR does not import unmerged document-evidence/export-review packages and does not query another service's application tables.
- Host composition remains responsible for storage credentials, TLS, encryption, bounded streaming, retention/legal-hold policy resolution, and malware/content safety policy where applicable.

## Alternatives rejected

- **Identifier + session authorization:** insufficient because it does not bind current document/Person/Employment/artifact/retention scope.
- **Audit after content release:** rejected because audit failure could leave an unrecorded disclosure.
- **Copy document content into audit evidence:** rejected because immutable audit should minimize PII/value exposure.
- **Import active PR-only packages directly:** rejected because it creates an undeclared stack and transfers unintegrated contracts/evidence.
- **Direct cross-service application-table SQL:** rejected because it violates dedicated ownership and modular extraction boundaries.

## Validation

The dedicated exact-head quality lane requires adversarial authorization/privacy/integrity tests, exact 100% owned production statement/branch coverage, isolated package installation, and clean checkout. Foundation, SAST, Security, Recovery, central required workflows, live review state, and effective rules remain independent merge gates.
