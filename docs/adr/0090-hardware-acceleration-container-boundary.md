# ADR 0090: Keep hardware acceleration outside the container boundary

- Status: Accepted
- Date: 2026-08-26
- Decision owner: Orgmetra
- Scope: All Orgmetra compute lanes (psychometrics/statistical kernels, services, CI)

## Context

Orgmetra runs its container workloads through Docker-compatible engines (Podman or colima on Apple-silicon developer machines, plain Docker in CI and Linux hosts). Statistical and psychometric arithmetic must stay Rust-first with CPU multithreading and GPU parity where material. Acceleration stacks differ per host: MLX exists only on Apple silicon as a native framework, CUDA requires the vendor driver plus matched kernel/user-space libraries inside the container, and OpenCL depends on host ICD (Installable Client Driver) discovery. A container that tries to own all of these becomes unportable, and a Rust kernel linked against one accelerator API cannot be re-linked by an orchestrator.

## Decision

1. Containers ship CPU-first. Every governed compute image executes correctly on plain CPU with Rayon-style bounded multithreading; this is the contract every deployment can rely on.
2. MLX is never used inside containers. On Apple-silicon hosts, acceleration is provided by a native sidecar service (a separate process/binary executed on the host) that exposes the same governed request/response contract as the in-container kernel. Containers talk to it over localhost HTTP/gRPC; they contain no MLX linkage.
3. CUDA is delivered through dedicated `*-cuda` image variants built from NVIDIA base images, enabled only when the runtime guarantees driver + toolkit parity (`--gpus all`, nvidia-container-toolkit). The default image variant never contains CUDA layers.
4. OpenCL follows the same variant rule: an `*-ocl` variant may exist only where the host ICD is mounted (`/etc/OpenCL/vendors`) and documented for that engine (Podman/colima device passthrough notes belong in the deployment README of the owning lane).
5. When an accelerator path cannot meet these boundary rules, it is split into its own service with its own repository/image rather than growing the core image. Native modules are separated services, not optional imports.
6. Selection between CPU and accelerated variants is a deployment-time choice recorded in the owning lane's operability documentation; results must be parity-checked against the CPU baseline using the lane's published accuracy regressions before a variant is promoted.

## Consequences

- Developer laptops (colima/Podman without GPU passthrough) get identical behavior to CI's CPU images; no silent numeric divergence from accidental host acceleration.
- Apple-silicon MLX gains are captured by the native sidecar without polluting image portability; the sidecar owns its own versioning and accuracy evidence.
- Image matrix grows by explicit variants (`cpu` default, `cuda`, `ocl`) instead of one monolithic image; each variant is built and scanned independently in CI.
- Kernel teams keep one Rust implementation; acceleration differences live behind the sidecar/variant boundary, not behind conditional compilation inside governed business logic.

## Verification

- Each compute lane's quality workflow pins the CPU variant in CI so coverage and accuracy regressions always prove the default contract.
- Variant promotion requires the lane's parity evidence (CPU vs accelerated outputs within published tolerances) recorded next to its traceability rows.

Status: Accepted
