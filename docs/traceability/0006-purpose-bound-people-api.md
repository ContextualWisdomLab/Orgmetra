# Purpose-bound People API traceability

| Requirement | Design decision | Implementation | Verification | Maturity |
| --- | --- | --- | --- | --- |
| Caller cannot select tenant | tenant comes only from `TokenAuthorizer` | `RequiredPurpose` | endpoint context assertion and source contract | implemented_on_active_pr |
| Caller cannot select purpose | fixed route dependencies | `RequiredPurpose("...")` | static purpose contract | implemented_on_active_pr |
| Missing/invalid token fails before data access | fail-closed bearer extraction | `auth.py`, `app.py` | authentication endpoint tests | implemented_on_active_pr |
| Insufficient purpose returns 403 | defensive allowed-purpose check | `ensure_purpose_authorized` | insufficient-principal test | implemented_on_active_pr |
| HR content is not echoed in errors | fixed RFC 9457 problems | `problems.py` | validation/repository/unexpected error tests | implemented_on_active_pr |
| Requests are finite | declared and observed byte counting | `RequestBoundaryMiddleware` | direct ASGI framing tests | implemented_on_active_pr |
| Blocking DB calls do not run on event loop | Starlette threadpool boundary | route handlers | endpoint workflow tests | implemented_on_active_pr |
| Person/candidate/link/audit operations are stable | explicit v1 routes and operation IDs | `create_app` | OpenAPI contract test | implemented_on_active_pr |
| Browser exposure is not accidentally permissive | docs UI disabled, no CORS default | app factory | source and endpoint tests | implemented_on_active_pr |
| CI is secret-minimal and immutable | read-only permissions and full action SHAs | quality workflow | workflow contract test | implemented_on_active_pr |
| Public code is explainable and fully exercised | docstring and exact coverage gates | quality workflow | Python 3.12/3.14 jobs | implemented_on_active_pr |
| Production identity federation is available | Keyverse OIDC/JWKS adapter | not implemented | none | planned |
| Dependency readiness is observable | database and identity readiness probes | not implemented | none | planned |
| Every framework error uses the same problem schema | HTTP exception normalization | partial: explicit errors only | unknown-route test exposes gap | planned |
| Overload is controlled | tenant rate limit and bounded threadpool | body limit only | load/backpressure evidence absent | planned |
| Release supply chain is attested | hashes, SBOM, provenance and digest images | exact pins/action SHAs only | release evidence absent | planned |

`implemented_on_active_pr` is not shipped behavior. Change it only after the full
stack merges into the protected default branch and fresh integrated acceptance
passes.
