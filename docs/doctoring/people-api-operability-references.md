# People API operability references

## Scope

These references support the active People API liveness/readiness design. They are design evidence only; they do not claim Kubernetes conformance, certification, production deployment, or release acceptance.

## APA 7 references

Kubernetes Authors. (2026). *Liveness, readiness, and startup probes*. Kubernetes. https://kubernetes.io/docs/concepts/workloads/pods/probes/

Kubernetes Authors. (2026). *Configure liveness, readiness and startup probes*. Kubernetes. https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/

## Design use

The Kubernetes documentation distinguishes liveness, which can trigger container restart, from readiness, which removes an unavailable Pod from service traffic. It also cautions that incorrectly coupling liveness to transient dependencies can create cascading failures and describes the pattern where readiness additionally verifies required backend services. Orgmetra applies that distinction by keeping `/health` dependency-free and binding `/ready` only to the People API's owned PostgreSQL availability check.
