import { readFile } from "node:fs/promises";

import { validateEmploymentSeparationAcceptance } from "./employment_separation_acceptance_contract.mjs";
import { requireAuthenticatedPerformanceEvidence } from "./employment_separation_authenticated_evidence_gate.mjs";
import { validatePinnedK6AcceptanceEvidence } from "./employment_separation_k6_evidence_contract.mjs";
import { parseRuntimeEvidenceArtifact } from "./employment_separation_runtime_evidence_artifact.mjs";

async function main() {
  // A caller-controlled digest is not an authentication boundary. Keep the
  // commercial entry point fail closed until the organization-owned signer and
  // verifier tracked by .github#2162 is released and consumed here.
  requireAuthenticatedPerformanceEvidence();

  const [resultPath, runtimeEvidencePath, fixturePath] = process.argv.slice(2);
  if (!resultPath || !runtimeEvidencePath || !fixturePath || process.argv.length !== 5) {
    throw new Error("usage: node employment_separation_acceptance_check.mjs <performance-result.json> <runtime-evidence.json> <performance-fixture.json>");
  }
  const [resultBytes, runtimeBytes, fixtureBytes] = await Promise.all([
    readFile(resultPath),
    readFile(runtimeEvidencePath),
    readFile(fixturePath),
  ]);
  const runtimeDocument = parseRuntimeEvidenceArtifact(runtimeBytes);
  const k6Evidence = validatePinnedK6AcceptanceEvidence(resultBytes, runtimeDocument.parsed);
  const evidenceContract = validateEmploymentSeparationAcceptance(
    resultBytes,
    runtimeDocument.parsed,
    fixtureBytes,
  );
  process.stdout.write(`${JSON.stringify({
    ...evidenceContract,
    ...k6Evidence,
    runtime_evidence_sha256: runtimeDocument.sha256,
  }, null, 2)}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
