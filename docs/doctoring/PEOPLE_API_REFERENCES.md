# People API references

This note records the standards and primary technical documentation used for
ADR-0006. References support design decisions but do not establish product or
customer certification.

## Decision traceability

| Decision | Basis | Repository evidence |
| --- | --- | --- |
| Bearer authentication is an explicit HTTP security scheme | RFC 6750; OpenID Connect Core | `TokenAuthorizer`, OpenAPI security scheme and authentication tests |
| Application errors are stable problem documents | RFC 9457 | `problems.py` and endpoint tests |
| Blocking repository calls leave the event loop | Starlette thread-pool contract | `run_in_threadpool` in route handlers |
| Request schemas reject unknown fields and values | FastAPI/Pydantic request validation | `schemas.py` and non-echo tests |
| Server selects purpose, not caller headers | NIST least privilege and access enforcement controls | `RequiredPurpose` and static source contract |
| Authorized PII remains usable under controls | NIST privacy/access/audit control families | purpose-bound context, RLS adapter and reference-only audit |
| Route dependencies stay server-owned at runtime | FastAPI dependency injection with runtime annotations | `app.py` `Depends` defaults and OpenAPI parameter contract |
| Bearer tokens reject hidden C0 separators | RFC 6750 printable token syntax | first-space split in `extract_bearer_token` |

## APA 7 references

Hardt, D. (2012). *The OAuth 2.0 authorization framework: Bearer token usage*
(RFC 6750). Internet Engineering Task Force.
https://doi.org/10.17487/RFC6750

Jones, M., Bradley, J., & Sakimura, N. (2014). *OpenID Connect Core 1.0
incorporating errata set 2*. OpenID Foundation.
https://openid.net/specs/openid-connect-core-1_0.html

Joint Task Force. (2020). *Security and privacy controls for information systems
and organizations* (NIST Special Publication 800-53, Revision 5). National
Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

Nottingham, M., Wilde, E., & Dalal, S. (2023). *Problem details for HTTP APIs*
(RFC 9457). Internet Engineering Task Force.
https://doi.org/10.17487/RFC9457

Ramírez, S. (2026). *FastAPI documentation: Dependencies in path operation
functions*. FastAPI. https://fastapi.tiangolo.com/tutorial/dependencies/

Ramírez, S. (2026). *FastAPI documentation: Security and dependencies*.
FastAPI. https://fastapi.tiangolo.com/tutorial/security/

Starlette. (2026). *Thread pool*. https://www.starlette.io/threadpool/

## Interpretation limits

- RFC 6750 does not define the tenant or HR purpose model.
- OpenID Connect verification still requires issuer, audience, algorithm, time,
  key lifecycle and deployment-specific policy.
- RFC 9457 defines an error representation, not authorization behavior.
- FastAPI and Starlette documentation describes framework behavior; exact pinned
  dependency versions and executable tests remain authoritative for this PR.
