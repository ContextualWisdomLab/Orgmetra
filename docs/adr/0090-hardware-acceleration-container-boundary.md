# ADR 0090: Keep hardware acceleration outside the container boundary

- Status: Accepted
- Date: 2026-08-26
- Decision owner: Orgmetra
- Scope: All Orgmetra compute lanes (psychometrics/statistical kernels, services, CI)

## Context

Orgmetra runs its container workloads through Docker-compatible engines (Podman or Colima on Apple-silicon developer machines, plain Docker in CI and Linux hosts). Statistical and psychometric arithmetic must stay Rust-first with CPU multithreading and GPU parity where material. Acceleration stacks differ per host: MLX exists only on Apple silicon as a native framework, CUDA requires the vendor driver plus matched kernel/user-space libraries inside the container, and OpenCL depends on host ICD (Installable Client Driver) discovery. A container that tries to own all of these becomes unportable, and a Rust kernel linked against one accelerator API cannot be re-linked by an orchestrator.

A container's loopback interface is not the macOS/Linux host loopback interface. A native accelerator process therefore needs an explicit container-to-host route rather than an ambiguous `localhost` promise. Docker documents `host.docker.internal` and the `host-gateway` mapping for host services; Podman documents `host.containers.internal`/`host.docker.internal` backed by its host-gateway resolution; Colima's current default configuration maps `host.docker.internal` through `host.lima.internal`. Deployments must verify the route rather than assuming that a hostname exists on every engine/network mode.

## Decision

1. Containers ship CPU-first. Every governed compute image executes correctly on plain CPU with Rayon-style bounded multithreading; this is the contract every deployment can rely on.
2. MLX is never used inside containers. On Apple-silicon hosts, acceleration is provided by a native sidecar service (a separate process/binary executed on the host) that exposes the same governed request/response contract as the in-container kernel. The endpoint is an explicit deployment input, never implicit `localhost`:
   - Docker Desktop and Colima/Docker use `host.docker.internal:<port>` only after a deployment preflight proves that name resolves to the intended host route. On Linux Docker, deployments that do not already provide that name must add `host.docker.internal:host-gateway` explicitly.
   - Podman uses `host.containers.internal:<port>` after preflight resolution. If automatic host-gateway discovery is unavailable, the deployment must configure an explicit `host-gateway`/`host_containers_internal_ip` mapping rather than guessing an address.
   - The sidecar bind address is a deliberately configured host interface reachable from the container/VM gateway and restricted to that local bridge/VM path. It must not be loopback-only for a bridged container path, and it must not be exposed on an unrestricted public/LAN interface merely to make routing work.
   - Production sidecar ingress is deny-by-default. Deployment preflight derives an allowlist limited to the intended container/VM bridge source range, and the listener rejects connections outside that ingress allowlist before request payload parsing. Network location is defense in depth only; it is never treated as client identity.
   - Every enabled caller authenticates with mutual TLS (mTLS) using a deployment-provisioned client certificate. The sidecar authorizes the authenticated client identity against an allowlist for the exact accelerator contract revision and operation set before reading model or HR payload bytes. An untrusted certificate, wrong client identity, unauthorized operation/revision, or disallowed ingress source fails closed as `accelerator_unavailable`. If mTLS identity verification and the ingress allowlist cannot be enforced on the selected engine/path, the accelerated path is disabled.
   - Before accelerated work is accepted, the authenticated and authorized caller performs name resolution, connection, and a health/version handshake that proves the expected contract revision. Routing, connection, authentication, authorization, ingress, or version mismatch fails closed as `accelerator_unavailable`; there is **no silent CPU fallback** inside an already selected accelerated request. An operator may explicitly select the CPU deployment path and submit a new governed request.
3. CUDA is delivered through dedicated `*-cuda` image variants built from NVIDIA base images, enabled only when the runtime guarantees driver + toolkit parity (`--gpus all`, nvidia-container-toolkit). The default image variant never contains CUDA layers.
4. OpenCL follows the same variant rule: an `*-ocl` variant may exist only where the host ICD is mounted (`/etc/OpenCL/vendors`) and documented for that engine (Podman/Colima device passthrough notes belong in the deployment README of the owning lane).
5. When an accelerator path cannot meet these boundary rules, it is split into its own service with its own repository/image rather than growing the core image. Native modules are separated services, not optional imports.
6. Selection between CPU and accelerated variants is a deployment-time choice recorded in the owning lane's operability documentation; results must be parity-checked against the CPU baseline using the lane's published accuracy regressions before a variant is promoted.

## Consequences

- Developer laptops (Colima/Podman without GPU passthrough) get identical behavior to CI's CPU images; no silent numeric divergence from accidental host acceleration.
- Apple-silicon MLX gains are captured by the native sidecar without polluting image portability; the sidecar owns its own versioning and accuracy evidence.
- Image matrix grows by explicit variants (`cpu` default, `cuda`, `ocl`) instead of one monolithic image; each variant is built and scanned independently in CI.
- Kernel teams keep one Rust implementation; acceleration differences live behind the sidecar/variant boundary, not behind conditional compilation inside governed business logic.
- Sidecar reachability is a deployment contract with an explicit fail-closed state, not a best-effort networking assumption.

## Verification

- Each compute lane's quality workflow pins the CPU variant in CI so coverage and accuracy regressions always prove the default contract.
- Variant promotion requires the lane's parity evidence (CPU vs accelerated outputs within published tolerances) recorded next to its traceability rows.
- Deployment verification must prove the configured host route resolves from the actual container engine, ingress is limited to the intended bridge/VM source range, an untrusted client certificate or unauthorized client identity/operation is rejected before payload handling, the health/version handshake succeeds, and any unreachable, unauthorized, or mismatched sidecar produces `accelerator_unavailable` without silently changing compute paths.

## Primary technical sources

- Docker, Inc. (2026). *docker container run: Add entries to container hosts file (--add-host).* https://docs.docker.com/reference/cli/docker/container/run/
- Docker, Inc. (2026). *Explore networking how-tos on Docker Desktop: Connect a container to a service on the host.* https://docs.docker.com/desktop/features/networking/networking-how-tos/
- Podman. (2026). *podman-run: --add-host and host-gateway.* https://docs.podman.io/en/latest/markdown/podman-run.1.html
- Colima. (2026). *Default network configuration (`dnsHosts`: `host.docker.internal` → `host.lima.internal`).* https://github.com/abiosoft/colima/blob/main/embedded/defaults/colima.yaml

Status: Accepted
