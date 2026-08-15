# Security

## Trust boundaries

- Orgmetra HRIS facts
- External CWL service references
- Document artifacts
- LLM draft outputs
- Assessment result snapshots
- PII fields
- Audit/provenance records

## Security principles

- Purpose-bound authorization replaces indiscriminate masking.
- Sensitive data access is auditable and scoped.
- LLM outputs cannot mutate authoritative facts without human-approved commands.
- External integrations use explicit adapters and fail closed.
- Event payloads carry opaque references, not broad PII broadcasts.
- Credentials and passkeys remain in Keyverse or external secret managers.

## High-risk actions

The following require explicit preview, evidence, actor, purpose, and audit:

- selection decision
- compensation change
- termination
- promotion
- job profile publication
- validation study policy change
- data export
- identity deprovisioning
