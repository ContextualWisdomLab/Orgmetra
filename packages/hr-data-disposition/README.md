# Orgmetra HR Data Disposition Request

This package creates a **request for authoritative disposition execution review**. It does not delete, pseudonymize, archive, encrypt, destroy, or sanitize HR data, and it does not grant an executor permission to do those things.

## When this boundary is usable

A request is accepted only when the upstream retention review already says that the reviewed due date has elapsed and that the review itself is still `not_authorized_to_delete`. The request also requires a currently reviewed `clear` legal-hold state and a review date strictly after the retention due date. A record on its due date is therefore still retained rather than treated as disposable.

The request binds only governance metadata and opaque references:

- tenant and target-resource references;
- the exact upstream retention-review reference and SHA-256 digest;
- record category and retention-policy reference/digest;
- reviewed retention due date and review date;
- clear legal-hold state;
- one closed requested disposition action;
- distinct requester and reviewer actor references;
- evidence version and exact UTC system-recorded time.

No candidate/worker name, email, salary, assessment score, free-form HR payload, copied policy text, credential, or secret is part of the request. The request type is runtime-final so a caller cannot subclass it and replace derived non-authorizing properties with forged execution authority before canonical serialization.

Construction seals the canonical request digest in a process-local identity-keyed weak registry outside packet-writable state. Canonicalization revalidates live fields and rejects a different valid policy, actor, date, or upstream-evidence value instead of creating a second audit fact; a caller cannot replace an in-object seal. Durable append-only audit, replay/idempotency, and execution authorization remain separate authoritative responsibilities.

## Closed actions

The current contract permits only `delete_application_record` and `pseudonymize_derived_record` as *requested* actions. The request always remains `execution_authorization_state=not_authorized_to_execute`, `scope_verification_state=requires_authoritative_resolution`, and `human_review_required=true`.

Before any future executor acts, the owning Orgmetra service must independently re-resolve the exact retention review and policy, current legal-hold state, tenant/resource scope, requester/reviewer authority, and immutable audit evidence, then obtain separate human execution approval. No direct cross-service application-table SQL is permitted.

## Application deletion is not media sanitization

NIST SP 800-88 Rev. 2 defines media sanitization as a storage/media assurance problem: access to target data on the media must be rendered infeasible for the relevant effort level, within an enterprise sanitization program. An application-layer disposition request cannot prove that outcome. For that reason this contract always emits `media_sanitization_state=not_claimed`; storage or infrastructure owners must produce any later sanitization/validation evidence through their own governed boundary.

## Verification

Run the package quality contract with:

```bash
PYTHONPATH=packages/hr-data-disposition/src \
  python -m pytest -c packages/hr-data-disposition/pyproject.toml \
  packages/hr-data-disposition/tests
```

Owned production statement and branch coverage are required to remain exactly 100%.
