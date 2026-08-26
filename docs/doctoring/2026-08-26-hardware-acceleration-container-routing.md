# Hardware-acceleration container routing — primary-source doctoring

## Scope

This note supports ADR 0090's container-to-host routing contract for an Apple-silicon MLX process that remains native to the host while Orgmetra application workloads remain containerized. It is research support for the ADR, not evidence that an accelerator implementation or deployment has been released.

## Findings

Docker documents `host.docker.internal` as the special host name for container-to-host access on Docker Desktop and documents the `host-gateway` value for explicit host mapping. Podman documents automatic `host.containers.internal` and `host.docker.internal` entries backed by host-gateway discovery, while warning that discovery can fail and then requires explicit configuration. Colima's current default configuration maps `host.docker.internal` to `host.lima.internal` through its internal resolver. These contracts make an unqualified `localhost` endpoint incorrect for a normal bridged container: the endpoint must be explicit, verified from the real engine/network mode, and unavailable routing must fail closed rather than silently changing the selected compute path.

The security consequence is equally important: making a native sidecar reachable must not be implemented by indiscriminately binding it to every external interface. The deployment lane must choose a host-reachable local bridge/VM interface, restrict ingress to that path, and prove a health/version handshake before accelerated work is accepted.

## APA 7 references

Colima. (2026). *Default Colima configuration*. GitHub. Retrieved August 26, 2026, from https://github.com/abiosoft/colima/blob/main/embedded/defaults/colima.yaml

Docker, Inc. (2026). *docker container run*. Docker Docs. Retrieved August 26, 2026, from https://docs.docker.com/reference/cli/docker/container/run/

Docker, Inc. (2026). *Explore networking how-tos on Docker Desktop*. Docker Docs. Retrieved August 26, 2026, from https://docs.docker.com/desktop/features/networking/networking-how-tos/

Podman. (2026). *podman-run*. Podman documentation. Retrieved August 26, 2026, from https://docs.podman.io/en/latest/markdown/podman-run.1.html
