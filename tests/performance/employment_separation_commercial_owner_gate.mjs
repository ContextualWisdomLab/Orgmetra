import { requireAuthenticatedDeploymentEvidence } from "./employment_separation_deployment_evidence_gate.mjs";
import { requireAuthenticatedPerformanceEvidence } from "./employment_separation_authenticated_evidence_gate.mjs";

export function requireCommercialPerformanceAuthorities() {
  const failures = [];
  for (const gate of [
    requireAuthenticatedPerformanceEvidence,
    requireAuthenticatedDeploymentEvidence,
  ]) {
    try {
      gate();
    } catch (error) {
      failures.push(error instanceof Error ? error.message : String(error));
    }
  }
  if (failures.length !== 0) {
    throw new Error(failures.join("\n"));
  }
}
