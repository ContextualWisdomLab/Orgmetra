# Changelog

## Unreleased

- Add a purpose-bound model-assisted Job Analysis draft workflow that requires exact tenant/Job Analysis snapshot authorization before model work.
- Require Task/FJA/KSAO semantic-unit coverage with content and source-provenance SHA-256 evidence while excluding raw semantic text from durable receipts.
- Bind untrusted draft output to an exact reviewed orchestration revision, route, digest, and orchestration provenance.
- Require a distinct accountable human reviewer and keep both confirmed and rejected drafts non-authoritative for Job Analysis persistence or employment decisions.
- Preserve the controlled human-review reason code in durable receipt evidence so a rejection or confirmation remains auditable without storing free-form review text.
- Preserve the exact authorizing evidence digest in durable receipt evidence so later audit correlation identifies the scope decision used for the draft.
- Give rejected drafts a revision-only next action instead of telling downstream users or agents to submit human-rejected evidence to authoritative persistence.
- Fail closed on hostile runtime subtypes, malformed references/digests/timestamps, scope mismatch, chronology errors, callback-result type forgery, and request/model mutation across authority, orchestration, and human-review calls.
- Seal issued receipt evidence outside caller-writable receipt fields and detect post-issuance canonical-evidence mutation.
- Require the runtime outcome's draft bytes to match the reviewed receipt digest on construction and every read, preventing a caller from pairing or later mutating unrelated text next to valid receipt evidence.
- Bound public Python support to the hosted 3.14 minor, pin exact CPython 3.14.7 in quality automation, install the reviewed setuptools 84.0.0 backend by SHA-256, and hash-bind the locally built exact-checkout wheel before isolated installation.
- Add exact-head CI with beginner-readable docstring validation and exact 100% owned production statement/branch coverage.
