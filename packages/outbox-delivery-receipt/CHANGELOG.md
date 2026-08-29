# Changelog

## Unreleased

- Define value-minimized external transport delivery receipt evidence.
- Bind receipts to an exact tenant/outbox/audit/target/attempt coordinate.
- Keep transport evidence untrusted and explicitly non-authorizing for delivery-state
  mutation.
- Require canonical UTC chronology, opaque normalized receipt references, SHA-256 artifact
  correlation, structural immutability, copy-bypass revalidation, and exact 100% owned
  statement/branch coverage.
- Detach caller-owned timezone behavior into built-in UTC timestamps before evidence is
  retained, reject behavior-overriding trust/identifier string subclasses, and reject
  receipt subclasses at exact-attempt verification so canonical evidence and returned
  digests cannot be rewritten through caller-controlled runtime behavior.
