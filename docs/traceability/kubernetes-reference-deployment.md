# Kubernetes reference deployment traceability

## State legend

- **Protected-main truth:** accepted on `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`.
- **Active PR:** implemented only on `feat/kubernetes-reference-deployment` until merged.
- **Dependency-active PR:** same-repository capability required for a runnable release but not copied into this branch.
- **Planned:** deliberately outside this bounded slice.

## Requirement → evidence map

| Requirement | State | Executable / review evidence |
| --- | --- | --- |
| Provider-neutral Kubernetes reference is absent on protected main and cannot be mistaken for shipped deployment truth | Protected-main truth | Foundation implementation plan Task 10 plus initial RED exact head `18778945f2bdb9d6f42cebd7a3c71c18dad36352` |
| Reference uses immutable image identity rather than a mutable tag | Active PR | `infrastructure/kubernetes/people-api-reference.json`; sentinel requires digest resolution before apply; `tests/kubernetes-reference.test.mjs` |
| Pod uses Restricted-intent security context and no automatic API token | Active PR | Namespace labels, ServiceAccount, Deployment security contexts and adversarial manifest assertions |
| Startup/liveness and readiness are not conflated | Active PR + dependency-active PR | Reference sends startup/liveness to `/health` and readiness to `/ready`; People API probe implementation is owned by PR #74 and must be integrated into the selected release image before this manifest can be runnable |
| Namespace traffic is deny-by-default | Active PR | `orgmetra-default-deny` plus exact People API ingress/PostgreSQL/DNS exceptions; network-policy assertions |
| Managed PostgreSQL adaptation cannot silently broaden egress | Active PR | `infrastructure/kubernetes/README.md` requires provider-approved exact private-network adaptation while preserving default deny |
| Voluntary disruption and rollout are bounded | Active PR | two replicas, `maxUnavailable: 0` rolling update, PDB `maxUnavailable: 1`, topology-spread preference |
| Target cluster validates object schemas/admission before deployment | Active PR | documented `kubectl apply --dry-run=server ...` precondition; actual target-cluster dry-run remains environment-specific release evidence |
| Release candidate has reproducible source/SBOM/provenance evidence | Dependency-active PR | PR #78; this branch does not duplicate its builder or evidence |
| Image/container build, signed attestation and verified deployable digest exist | Planned | must be produced from one accepted integrated protected head; sentinel intentionally keeps this reference non-runnable until then |
| Production metrics, ingress/TLS, secrets delivery, autoscaling and environment-specific SLOs are accepted | Planned | separate deployment/operability slices; not claimed here |

## RED → repair evidence

The exact RED head `18778945f2bdb9d6f42cebd7a3c71c18dad36352` materialized Kubernetes Reference Quality run `32564001046`, job `97009809481`. The job proved exact checkout of that SHA and failed in the first contract step because `infrastructure/kubernetes/people-api-reference.json` and `infrastructure/kubernetes/README.md` did not exist. Six deployment-contract tests failed with `ENOENT`; repository validation and clean-checkout proof were therefore correctly skipped rather than treated as passing evidence.

The repair adds only Orgmetra-owned reference-deployment artifacts and supporting evidence. It does not mutate a dedicated-writer CWL dependency, add cross-service SQL, publish an image, create cluster resources, or claim that a target cluster has accepted the objects.

## Release boundary

A release operator must replace the image sentinel only with a verified digest from the same exact integrated protected revision that contains the required People API probe implementation and passes all applicable build, security, provenance, review, migration, rollback/recovery and target-environment checks together. The checked-in reference itself is therefore buyer-readable deployment intent, not release authorization.
