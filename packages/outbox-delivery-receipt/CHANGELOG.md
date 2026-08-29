# Changelog

## Unreleased

- Define value-minimized external transport delivery receipt evidence.
- Bind receipts to an exact tenant/outbox/audit/target/attempt coordinate.
- Keep transport evidence untrusted and explicitly non-authorizing for delivery-state
  mutation.
- Require canonical UTC chronology, opaque normalized receipt references, SHA-256 artifact
  correlation, structural immutability, copy-bypass revalidation, and exact 100% owned
  statement/branch coverage.
