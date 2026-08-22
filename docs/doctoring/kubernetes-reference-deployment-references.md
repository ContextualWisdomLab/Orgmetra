# Kubernetes reference deployment — primary-source doctoring

**Evidence state:** active-PR design evidence. These sources inform the Orgmetra-owned reference deployment; they do not constitute Kubernetes certification, cloud-provider compatibility, SOC 2 evidence by themselves, or release authorization.

## APA 7 references

Kubernetes Authors. (n.d.). *Configure liveness, readiness and startup probes*. Kubernetes. Retrieved August 22, 2026, from https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/

Kubernetes Authors. (n.d.). *Network policies*. Kubernetes. Retrieved August 22, 2026, from https://kubernetes.io/docs/concepts/services-networking/network-policies/

Kubernetes Authors. (n.d.). *Pod security standards*. Kubernetes. Retrieved August 22, 2026, from https://kubernetes.io/docs/concepts/security/pod-security-standards/

Kubernetes Authors. (n.d.). *Specifying a disruption budget for your application*. Kubernetes. Retrieved August 22, 2026, from https://kubernetes.io/docs/tasks/run-application/configure-pdb/

## Design consequences recorded from the primary documentation

- **Probe roles stay separate.** Startup probes delay takeover by liveness/readiness while a process starts; liveness is for restart decisions; readiness controls whether a pod receives service traffic. Orgmetra therefore keeps `/health` dependency-free and uses `/ready` for owned PostgreSQL readiness rather than making database reachability a liveness condition.
- **Restricted pod intent is explicit.** The reference declares Restricted Pod Security Admission labels and a pod/container security context that avoids host namespaces, privileged mode and privilege escalation, runs non-root, uses `RuntimeDefault` seccomp and drops Linux capabilities.
- **Network isolation starts deny-by-default.** A NetworkPolicy selecting all pods with both `Ingress` and `Egress` policy types establishes the namespace baseline. Required application and DNS flows are then explicit exceptions. Cluster networking must actually enforce NetworkPolicy before this is treated as isolation evidence.
- **PDB evidence is bounded.** `maxUnavailable: 1` applies to a controller-managed replicated Deployment and limits voluntary evictions; it is not evidence against involuntary node, process or dependency failures.

## Out of scope for this evidence set

This doctoring file does not select a managed Kubernetes vendor, CNI, ingress controller, service mesh, cloud load balancer, registry, PostgreSQL provider or image signer. Those choices must be bound to their own current primary documentation and target-environment acceptance evidence before release.
