# People API operational telemetry traceability

## Truth status

- **Protected-main truth:** `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` exposes governed People HTTP boundaries and candidate SLOs, but it does not contain a People HTTP measurement middleware or an OpenTelemetry exporter.
- **Active PR truth:** PR #90 adds an adapter-neutral, privacy-minimized request-completion measurement boundary in `orgmetra_people_api.telemetry`.
- **Not claimed:** this slice does not configure an OpenTelemetry SDK/Collector, export OTLP, publish dashboards or alerts, prove an SLO, instrument database calls, or make a release/deployment claim.

## Buyer-visible requirement to executable evidence

| Requirement | Executable boundary | Regression evidence |
| --- | --- | --- |
| Request latency can be measured without copying HR identifiers | `PeopleHttpTelemetryMiddleware` emits `duration_seconds` with only a known route template or `None` | `test_emits_duration_without_identifying_request_values`, `test_unknown_route_never_uses_raw_path_as_metric_route` |
| Route dimensions stay low-cardinality | `classify_people_http_route` recognizes only five application-owned People route templates and never substitutes a raw path | `test_classifies_only_known_low_cardinality_people_routes` |
| HTTP methods stay bounded | `normalize_http_method` emits the reviewed known method set or `_OTHER`; exact built-in strings prevent hostile runtime equality/hash behavior | `test_normalizes_unknown_or_runtime_subclass_methods_to_other` |
| Server errors are aggregatable without backend exception disclosure | HTTP 5xx uses its decimal status string; any propagated exception uses `unhandled_exception` regardless of response-status capture; a missing response start uses `missing_response_status` | `test_records_server_error_as_low_cardinality_status_error_type`, `test_unhandled_exception_is_measured_then_reraised`, `test_missing_response_start_is_bounded_operational_error` |
| Successful/client-error requests do not manufacture server-error dimensions | status < 500 leaves `error_type` unset | `test_does_not_mark_client_error_as_server_failure` |
| Telemetry outage cannot deny governed HR work | sink/measurement failures are caught after the wrapped request outcome is determined; only bounded operator metadata is logged | `test_exporter_failure_never_breaks_people_response` |
| ASGI non-HTTP scopes are not mislabeled as HTTP traffic | non-HTTP scopes pass directly to the wrapped app | `test_non_http_scope_passes_through_without_measurement` |
| Invalid direct measurement construction fails closed | `PeopleHttpRequestMeasurement` validates exact types, finite duration, status range, route allow-list and error/status consistency | `test_measurement_rejects_unbounded_or_noncanonical_dimensions` |
| Middleware wiring fails before traffic when dependencies are unusable | constructor validates wrapped app, metric sink method and monotonic clock callability | `test_rejects_unusable_middleware_dependencies_before_traffic` |
| Response status capture is deterministic | middleware records the first valid integer HTTP response status and ignores invalid/duplicate starts | `test_ignores_invalid_and_duplicate_response_start_statuses` |

## Privacy and cardinality boundary

The measurement deliberately excludes tenant, Person, Candidate, Employment, Position and Assignment identifiers; raw URL/path values; query strings; headers; bearer credentials; actor references; request/response bodies; HR values; support references; exception messages; database details; and foreign-service identifiers. Unknown routes produce `route_template=None` rather than a caller-controlled string.

The sink receives a completed immutable measurement. Exporters may translate that measurement to their backend, but they must not enrich it with PII or uncontrolled request attributes. Export is non-authoritative and best-effort: telemetry loss is operationally visible but cannot change authorization, mutation, read, hire, audit/outbox, or HTTP outcome semantics.

## OpenTelemetry alignment boundary

The design is grounded in OpenTelemetry Semantic Conventions 1.44.0. It follows the stable HTTP server guidance that `http.server.request.duration` is measured in seconds, unknown request methods map to `_OTHER`, `http.route` is a low-cardinality route template rather than a raw path, and `error.type` is predictable and low-cardinality.

This package is **not** an OpenTelemetry instrumentation library and does not claim full Semantic Conventions conformance. A deployment adapter that maps the internal measurement to OpenTelemetry remains responsible for the current required/recommended resource/network attributes, exporter configuration, Collector policy, any deployment-specific override of recognized HTTP methods, histogram aggregation, temporality and retention. Those concerns must not be implemented by copying request PII into metric attributes.

## Owner boundaries

This slice writes only Orgmetra. Keyverse, Naruon, contextual-orchestrator, Psychometrics Commons, TEPP and other dedicated-writer CWL repositories remain read-only dependencies. No cross-service application-table SQL is introduced.
