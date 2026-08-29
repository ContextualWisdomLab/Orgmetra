# Traceability — purpose-bound HR document retrieval

## Truth boundary

At the branch point `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`, protected-main product code does not contain this executable retrieval boundary. This document describes active PR truth only until integration.

Separate active Orgmetra PRs own document metadata evidence/persistence and export-review evidence. Their checks, reviews, source code, and PR state do not transfer into this root lane. This lane consumes only injected host contracts and introduces no direct cross-service application-table SQL.

## Requirement mapping

| Requirement | Active-PR implementation / evidence |
|---|---|
| Purpose-bound authorization on every read | `retrieve_hr_document(...)` invokes `DocumentRetrievalAuthority` for the exact freshly resolved scope before artifact access. |
| Authorization remains current through protected storage access and release | The boundary validates authorization freshness after authority resolution, rechecks expiry after artifact verification, and checks again after immutable audit append immediately before byte release. The post-verification instant is the receipt `recorded_at`. |
| Exact tenant/document scope | Query and fresh scope must match tenant + document; authorization must also match Person, Employment, artifact, retention, classification, requester, purpose, reason, delivery context, and byte limit. |
| Current retention/legal-hold state | Fresh scope and authorization must agree on `retained_record` or `legal_hold_record`; disposed/unknown states fail closed. |
| Necessary PII remains usable | Authorized content is returned as exact bytes; the boundary does not indiscriminately mask document content. |
| Data minimization in durable evidence | Retrieval receipt excludes document bytes/text/title, free-form HR notes, compensation, assessments/ratings, credentials, and model output. |
| Bounded storage access | Artifact reader receives the authorized artifact reference plus exact byte limit; oversized content fails closed. |
| Content integrity | SHA-256 of exact returned bytes must equal both reader evidence and fresh authoritative metadata. |
| Audit before disclosure | Immutable receipt append must succeed before `DocumentRetrievalResult` is returned. |
| No high-impact decision authority | Result and receipt are fixed to `not_authorized_for_employment_decision`. |
| Runtime-integrity hardening | Exact built-in primitives, detached timezone-aware system values, output revalidation, host capability validation, and mutation regressions fail closed. |
| Python compatibility truth | Public metadata is bounded to `>=3.14,<3.15`, and the exact quality lane uses CPython 3.14.7; older or future minors are not claimed without separate exact evidence. |
| Test/package evidence | Dedicated quality lane requires exact 100% owned production statement/branch coverage, a reviewed SHA-256-locked build backend, a wheel built from the exact checkout whose computed SHA-256 is required again at isolated install, and a clean checkout. |

## Next integration action

After this PR integrates, bind concrete Orgmetra host adapters only through accepted integrated contracts: authoritative document metadata persistence, People/purpose authorization, configured artifact storage, and immutable audit/outbox. A customer-facing external download/export flow remains a separate governed execution boundary because internal authenticated retrieval does not itself authorize egress.
