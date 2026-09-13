import { readFile } from "node:fs/promises";

import { validateEmploymentSeparationAcceptance } from "./employment_separation_acceptance_contract.mjs";
import { validatePinnedK6AcceptanceEvidence } from "./employment_separation_k6_evidence_contract.mjs";
import { parseRuntimeEvidenceArtifact } from "./employment_separation_runtime_evidence_artifact.mjs";

async function main() {
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
  const acceptance = validateEmploymentSeparationAcceptance(
    resultBytes,
    runtimeDocument.parsed,
    fixtureBytes,
  );
  process.stdout.write(`${JSON.stringify({
    ...acceptance,
    ...k6Evidence,
    runtime_evidence_sha256: runtimeDocument.sha256,
  }, null, 2)}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
