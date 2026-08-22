# People API operational telemetry references

Accessed 2026-08-23. These references are engineering evidence for PR #90; they do not assert OpenTelemetry certification or complete Semantic Conventions conformance.

## APA 7 references

OpenTelemetry Authors. (2026). *OpenTelemetry semantic conventions 1.44.0*. OpenTelemetry. https://opentelemetry.io/docs/specs/semconv/

OpenTelemetry Authors. (2026). *Semantic conventions for HTTP metrics*. OpenTelemetry. https://opentelemetry.io/docs/specs/semconv/http/http-metrics/

OpenTelemetry Authors. (2026). *Semantic conventions for HTTP spans*. OpenTelemetry. https://opentelemetry.io/docs/specs/semconv/http/http-spans/

## Design consequences used by this slice

- The current Semantic Conventions release is 1.44.0.
- HTTP server request duration is represented by the stable `http.server.request.duration` metric in seconds; this slice stores a duration in seconds but leaves histogram/export configuration to the deployment adapter.
- A request method unknown to instrumentation maps to `_OTHER`, and method values are case-sensitive. PR #90 therefore does not place arbitrary request method text into its normal metric dimension.
- `http.route` is intended to be a low-cardinality application route and raw URI paths must not be substituted for it. PR #90 therefore recognizes only application-owned People route templates and emits no route value for unknown paths.
- `error.type` should be predictable and low-cardinality. Successful requests should not set it. PR #90 uses only decimal 5xx status strings plus two bounded middleware states (`unhandled_exception` and `missing_response_status`).
- The OpenTelemetry HTTP conventions include attributes beyond the internal measurement in this slice. A future exporter adapter must satisfy those current requirements itself and must not infer missing values by copying sensitive request metadata into metrics.
