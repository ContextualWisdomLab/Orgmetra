import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REFERENCE_PATH = path.join(
  ROOT,
  "infrastructure",
  "kubernetes",
  "people-api-reference.json",
);
const README_PATH = path.join(ROOT, "infrastructure", "kubernetes", "README.md");
const IMAGE_SENTINEL =
  "ghcr.io/contextualwisdomlab/orgmetra-people-api@sha256:__REPLACE_WITH_VERIFIED_64_HEX_DIGEST__";

function referenceDocument() {
  return JSON.parse(fs.readFileSync(REFERENCE_PATH, "utf8"));
}

function resource(document, kind, name) {
  const match = document.items.find(
    (item) => item.kind === kind && item.metadata?.name === name,
  );
  assert.ok(match, `missing ${kind}/${name}`);
  return match;
}

function peopleContainer(document) {
  const deployment = resource(document, "Deployment", "orgmetra-people-api");
  assert.equal(deployment.spec.template.spec.containers.length, 1);
  return deployment.spec.template.spec.containers[0];
}

test("reference contains the bounded deployment resource set", () => {
  const document = referenceDocument();
  assert.equal(document.apiVersion, "v1");
  assert.equal(document.kind, "List");
  assert.equal(document.items.length, 7);

  resource(document, "Namespace", "orgmetra-system");
  resource(document, "ServiceAccount", "orgmetra-people-api");
  resource(document, "Deployment", "orgmetra-people-api");
  resource(document, "Service", "orgmetra-people-api");
  resource(document, "PodDisruptionBudget", "orgmetra-people-api");
  resource(document, "NetworkPolicy", "orgmetra-default-deny");
  resource(document, "NetworkPolicy", "orgmetra-people-api-access");
});

test("namespace and workload align with restricted pod-security intent", () => {
  const document = referenceDocument();
  const namespace = resource(document, "Namespace", "orgmetra-system");
  assert.equal(
    namespace.metadata.labels["pod-security.kubernetes.io/enforce"],
    "restricted",
  );
  assert.equal(
    namespace.metadata.labels["pod-security.kubernetes.io/audit"],
    "restricted",
  );
  assert.equal(
    namespace.metadata.labels["pod-security.kubernetes.io/warn"],
    "restricted",
  );

  const serviceAccount = resource(
    document,
    "ServiceAccount",
    "orgmetra-people-api",
  );
  assert.equal(serviceAccount.automountServiceAccountToken, false);

  const deployment = resource(document, "Deployment", "orgmetra-people-api");
  const podSpec = deployment.spec.template.spec;
  assert.equal(podSpec.automountServiceAccountToken, false);
  assert.equal(podSpec.serviceAccountName, "orgmetra-people-api");
  assert.equal(podSpec.hostNetwork, false);
  assert.equal(podSpec.hostPID, false);
  assert.equal(podSpec.hostIPC, false);
  assert.equal(podSpec.enableServiceLinks, false);
  assert.equal(podSpec.securityContext.runAsNonRoot, true);
  assert.deepEqual(podSpec.securityContext.seccompProfile, {
    type: "RuntimeDefault",
  });

  for (const volume of podSpec.volumes ?? []) {
    assert.equal("hostPath" in volume, false, "hostPath volumes are forbidden");
  }

  const container = peopleContainer(document);
  assert.equal(container.image, IMAGE_SENTINEL);
  assert.equal(container.imagePullPolicy, "IfNotPresent");
  assert.equal(container.securityContext.privileged, false);
  assert.equal(container.securityContext.allowPrivilegeEscalation, false);
  assert.equal(container.securityContext.readOnlyRootFilesystem, true);
  assert.deepEqual(container.securityContext.capabilities, { drop: ["ALL"] });
  assert.equal("hostPort" in container.ports[0], false);
});

test("health probes preserve liveness/readiness separation", () => {
  const document = referenceDocument();
  const container = peopleContainer(document);

  assert.deepEqual(container.startupProbe.httpGet, {
    path: "/health",
    port: "http",
    scheme: "HTTP",
  });
  assert.equal(container.startupProbe.periodSeconds, 5);
  assert.equal(container.startupProbe.failureThreshold, 24);

  assert.deepEqual(container.livenessProbe.httpGet, {
    path: "/health",
    port: "http",
    scheme: "HTTP",
  });
  assert.equal(container.livenessProbe.periodSeconds, 10);
  assert.equal(container.livenessProbe.failureThreshold, 3);

  assert.deepEqual(container.readinessProbe.httpGet, {
    path: "/ready",
    port: "http",
    scheme: "HTTP",
  });
  assert.equal(container.readinessProbe.periodSeconds, 5);
  assert.equal(container.readinessProbe.failureThreshold, 2);
});

test("deployment bounds resources and voluntary disruption", () => {
  const document = referenceDocument();
  const deployment = resource(document, "Deployment", "orgmetra-people-api");
  const container = peopleContainer(document);

  assert.equal(deployment.spec.replicas, 2);
  assert.equal(deployment.spec.minReadySeconds, 10);
  assert.equal(deployment.spec.progressDeadlineSeconds, 300);
  assert.equal(deployment.spec.revisionHistoryLimit, 5);
  assert.deepEqual(deployment.spec.strategy, {
    type: "RollingUpdate",
    rollingUpdate: { maxUnavailable: 0, maxSurge: 1 },
  });
  assert.deepEqual(container.resources, {
    requests: { cpu: "100m", memory: "128Mi", "ephemeral-storage": "64Mi" },
    limits: { cpu: "1", memory: "512Mi", "ephemeral-storage": "256Mi" },
  });

  const pdb = resource(document, "PodDisruptionBudget", "orgmetra-people-api");
  assert.equal(pdb.apiVersion, "policy/v1");
  assert.equal(pdb.spec.maxUnavailable, 1);
  assert.deepEqual(pdb.spec.selector, {
    matchLabels: { "app.kubernetes.io/name": "orgmetra-people-api" },
  });
});

test("network policy is default-deny with explicit People API flows", () => {
  const document = referenceDocument();
  const deny = resource(document, "NetworkPolicy", "orgmetra-default-deny");
  assert.deepEqual(deny.spec.podSelector, {});
  assert.deepEqual(deny.spec.policyTypes, ["Ingress", "Egress"]);
  assert.deepEqual(deny.spec.ingress, []);
  assert.deepEqual(deny.spec.egress, []);

  const access = resource(
    document,
    "NetworkPolicy",
    "orgmetra-people-api-access",
  );
  assert.deepEqual(access.spec.policyTypes, ["Ingress", "Egress"]);
  assert.deepEqual(access.spec.podSelector, {
    matchLabels: { "app.kubernetes.io/name": "orgmetra-people-api" },
  });

  assert.deepEqual(access.spec.ingress, [
    {
      from: [
        {
          podSelector: {
            matchLabels: { "orgmetra.cwl/people-api-client": "true" },
          },
        },
      ],
      ports: [{ protocol: "TCP", port: 8080 }],
    },
  ]);

  assert.deepEqual(access.spec.egress, [
    {
      to: [
        {
          podSelector: {
            matchLabels: { "app.kubernetes.io/name": "orgmetra-postgres" },
          },
        },
      ],
      ports: [{ protocol: "TCP", port: 5432 }],
    },
    {
      to: [
        {
          namespaceSelector: {
            matchLabels: { "kubernetes.io/metadata.name": "kube-system" },
          },
          podSelector: { matchLabels: { "k8s-app": "kube-dns" } },
        },
      ],
      ports: [
        { protocol: "UDP", port: 53 },
        { protocol: "TCP", port: 53 },
      ],
    },
  ]);
});

test("reference documentation keeps digest resolution and database egress fail-closed", () => {
  const text = fs.readFileSync(README_PATH, "utf8");
  assert.match(text, /verified 64-character lowercase SHA-256 image digest/i);
  assert.match(text, /does not authorize a release/i);
  assert.match(text, /managed PostgreSQL/i);
  assert.match(text, /replace the database egress rule/i);
  assert.match(text, /NetworkPolicy-capable CNI/i);
  assert.match(text, /kubectl apply --dry-run=server/i);
  assert.match(text, /pod-security\.kubernetes\.io\/enforce=restricted/i);
});
