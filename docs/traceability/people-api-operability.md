# People API operability traceability

## Status

This document describes the active PR that introduces executable People API probe semantics. Protected `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` does not yet contain these routes, and this document does not claim production deployment or release readiness.

## Requirement-to-evidence map

| Requirement | Active implementation | Executable evidence | Failure rule |
|---|---|---|---|
| Process liveness must not depend on PostgreSQL availability | `PeopleOperabilityAsgiApp` `GET /health` | `test_health_is_live_without_touching_owned_dependencies` | PostgreSQL failure cannot make liveness fail or trigger a dependency call. |
| Traffic readiness must reflect the service-owned PostgreSQL dependency | `PeopleOperabilityAsgiApp` `GET /ready` + `PostgresReadinessProbe` | `test_ready_checks_owned_dependency_and_reports_success`, `test_postgres_probe_requires_callable_factory_and_a_result_row`, `test_postgres_probe_accepts_mapping_row_factory` | Readiness is 200 only after the reviewed read-only probe produces a row regardless of DB-API row factory. |
| Backend failure details must not cross the HTTP boundary | bounded `503 not_ready` response | `test_ready_normalizes_dependency_failure_without_leaking_details` | Any owned-dependency exception becomes a stable 503 with a next operator action and no backend message. |
| Probe routes must not become a hidden HR-data or identity integration path | no tenant context, credentials, HR table SQL, or foreign-service calls | source contract plus route tests | `/health` and `/ready` expose status only; Keyverse and other dedicated-writer services remain outside this boundary. |
| Unsupported transport shapes must stay bounded | exact GET-only `/health` and `/ready` surface | `test_unknown_route_and_wrong_method_are_bounded_transport_errors`, `test_non_http_scope_is_rejected_as_a_programming_error` | Unknown route is 404, wrong method is 405 with `Allow: GET`, non-HTTP ASGI is rejected. |

## Operational interpretation

Kubernetes distinguishes liveness from readiness: liveness is used to decide when a container should be restarted, while readiness determines whether it should receive traffic. The official Kubernetes probe guidance specifically warns that an incorrect liveness dependency can cause cascading restarts and notes that a strict backend dependency can be checked by readiness while liveness continues to reflect the application itself. Orgmetra therefore keeps PostgreSQL out of `/health` and checks it only in `/ready`.

The PostgreSQL readiness query deliberately proves infrastructure availability only. It does not prove tenant authorization, HR-data correctness, migration compatibility, downstream integrations, or release acceptance. The constant `SELECT 1` contract requires a result row but does not prescribe whether a DB-API driver represents that row as a tuple, mapping, or another row-factory-owned shape. Those concerns remain separate evidence gates.

## Ownership boundary

This slice writes only Orgmetra. PostgreSQL is an Orgmetra-owned runtime dependency. Keyverse, Naruon, contextual-orchestrator, and all other dedicated-writer CWL repositories are not queried or mutated by the probe and are not claimed healthy by its result.
