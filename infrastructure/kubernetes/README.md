# Orgmetra Kubernetes reference deployment

This directory contains a provider-neutral **reference**, not a release artifact. Applying it does not authorize a release, does not certify a cluster, and does not replace environment-specific threat modelling or change approval.

## Release precondition: immutable image identity

`people-api-reference.json` deliberately contains a non-runnable image sentinel. Before any server-side apply or rollout, replace it with an Orgmetra People API image qualified by a **verified 64-character lowercase SHA-256 image digest**:

```text
ghcr.io/contextualwisdomlab/orgmetra-people-api@sha256:<64-lowercase-hex>
```

The digest must be resolved from the same integrated protected source revision that passed the applicable build, security, SBOM, provenance, migration, recovery, review and release-authorization gates. A mutable tag is not an acceptable substitute. The current repository reference does not publish such an image and therefore must remain non-runnable until that evidence exists.

The probe paths also assume the selected image contains the governed People API `/health` and `/ready` contracts. Do not deploy a protected revision that predates those endpoints merely to satisfy the manifest shape.

## Pod hardening

The `orgmetra-system` namespace declares Restricted Pod Security Admission for `enforce`, `audit`, and `warn`, and pins all three policy modes to Kubernetes minor `v1.37`. The explicit version labels are deliberate: an omitted version uses the admission controller's `latest` policy, which can change the effective Restricted contract after a Kubernetes upgrade. The People API pod is non-root, uses `RuntimeDefault` seccomp, disables service-account token automount, privilege escalation, privileged mode and host namespaces, drops every Linux capability, and uses a read-only root filesystem. Because the root filesystem is read-only, the pod declares a dedicated `tmp-scratch` `emptyDir` mounted at `/tmp`; do not remove it and do not replace it with a `hostPath`.

Cluster operators must verify that admission controls actually enforce the intended Restricted profile. A target cluster whose supported policy minor differs from `v1.37` must not make the reference deployable by deleting or weakening the version labels. Re-baseline the policy deliberately against that cluster's authoritative Kubernetes documentation, update the pinned minor and regression evidence together, and prove the resulting objects with server-side dry-run before release. If the environment injects sidecars or init containers, those injected containers must independently satisfy the same effective policy.

## Liveness and readiness

- startup and liveness use `GET /health`, which is process-liveness only;
- readiness uses `GET /ready`, which checks the People API's owned PostgreSQL dependency;
- dependency failure removes a pod from service traffic rather than making liveness depend on PostgreSQL.

The timing values are bounded reference defaults, not universal tuning values. Validate them against measured startup and dependency-recovery behaviour before production use.

## Network isolation

The namespace starts from default-deny ingress and egress. The People API policy then permits only:

1. TCP/8080 ingress from same-namespace pods explicitly labelled `orgmetra.cwl/people-api-client=true`;
2. TCP/8080 ingress from the kubelet probe source range, modelled by the RFC 5737 TEST-NET-1 placeholder `192.0.2.0/24`. **Replace that `ipBlock.cidr` with the exact node CIDR your cluster's kubelet probes originate from** (or the documented per-node ranges); without it, a default-deny CNI drops HTTP health probes and every pod fails liveness;
3. TCP/5432 egress to same-namespace pods labelled `app.kubernetes.io/name=orgmetra-postgres`;
4. DNS to kube-system pods labelled `k8s-app=kube-dns` over UDP/TCP 53.

A **NetworkPolicy-capable CNI** is required. If the selected cluster networking implementation does not enforce Kubernetes NetworkPolicy, do not claim that this reference provides network isolation.

The checked-in PostgreSQL rule models an in-cluster owned database. For **managed PostgreSQL**, replace the database egress rule with the provider-approved private-network policy for the exact database endpoints while preserving default-deny semantics. Do not broaden egress to `0.0.0.0/0` as a convenience workaround. Likewise, adapt the DNS selector only to the cluster's authoritative DNS implementation and keep that exception narrowly scoped.

Keyverse, Naruon and other dedicated-writer CWL services are intentionally absent from this egress policy. Add a foreign-service network path only when a published adapter/API contract and environment-specific authorization design require it; never add cross-service application-table access.

## Availability boundary

The reference uses two replicas, a rolling update with `maxUnavailable: 0`, and a PodDisruptionBudget with `maxUnavailable: 1`. The PDB constrains voluntary disruption only; it does not protect against node failure or application failure. A topology-spread preference reduces accidental same-node concentration but does not claim multi-zone disaster tolerance.

## Pre-deployment verification

Do not apply the reference unchanged. After resolving the exact image digest and cluster-specific database/DNS networking, validate the candidate against the target API server:

```bash
kubectl apply --dry-run=server -f infrastructure/kubernetes/people-api-reference.json
```

Then verify, at minimum, the target cluster's admission policy, NetworkPolicy enforcement, available resource quotas, image-pull authorization, probe behaviour, disruption semantics, PostgreSQL connectivity, migration compatibility, rollback/recovery procedure and immutable release evidence. A successful dry-run is necessary evidence for the target cluster but is not sufficient release authorization.
