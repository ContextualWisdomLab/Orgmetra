# Orgmetra HR Data-Rights Request Evidence

This package defines an Orgmetra-owned, value-minimized request-intake boundary for HR privacy/data-rights workflows. It records **that a request was submitted and what governed action was requested**; it does not decide whether a jurisdiction, contract, policy, or employment context creates an entitlement, and it does not authorize disclosure, correction, deletion, restriction, export, or any employment action.

## What this boundary records

A request packet binds one tenant, one opaque packet-owned request reference, one opaque Person reference, one pseudonymous requester correlation, identity-resolution evidence, source-submission evidence, the reviewed applicable-policy reference and digest, a bounded requester role, a bounded requested action, a bounded intake channel, evidence version, human/business submission time, and later-or-equal system-recorded time.

Canonical evidence intentionally carries no HR field values, name, email address, phone number, employee number, compensation value, request body, legal narrative, credential, token, or model output.

Supported request-intent codes are operational routing vocabulary only:

- `access_copy`
- `correct_record`
- `delete_record`
- `restrict_processing`

Every packet remains `requires_authoritative_policy_review`, `not_authorized_to_disclose`, and `not_authorized_to_modify_hr_data`. A downstream host must re-resolve tenant, Person, requester identity/authority, applicable policy/jurisdiction, retention/legal-hold state, export scope, and immutable audit/outbox evidence before fulfillment. Existing Orgmetra export, retention/disposition, People authorization, and audit boundaries remain authoritative; this package does not bypass them.

## Ownership and deployment

This is an Orgmetra-local evidence contract. It does not write Keyverse or any other dedicated-writer CWL repository and performs no cross-service application-table SQL. `requester_actor_reference` is an Orgmetra-local pseudonymous correlation after identity resolution, not an identity-provider subject format.

The package currently targets the repository's reviewed CPython 3.14.7 runtime. Its dedicated quality workflow builds the exact wheel, installs the repository's hash-pinned test toolchain in a fully isolated environment, hash-binds the generated wheel at install time, runs exact statement/branch coverage, and requires a clean checkout.

## Standards posture

The design uses the **final NIST Privacy Framework 1.0** as a technology-, sector-, law-, and jurisdiction-agnostic privacy-risk-management input. As of the 2026-08-23 review, NIST Privacy Framework 1.1 remains an Initial Public Draft / forthcoming final and is not represented here as a final standard. GDPR Articles 15–17 are recorded only as examples showing that access, rectification, and erasure requests can have distinct conditions and consequences; Orgmetra does **not** infer legal eligibility from a request code. See `docs/doctoring/hr-data-rights-request-references.md`.

No NIST, GDPR, SOC 2, legal-compliance, or certification claim is made by this package.
