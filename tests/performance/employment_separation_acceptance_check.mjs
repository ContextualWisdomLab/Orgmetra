import { readFile } from "node:fs/promises";

import { validateEmploymentSeparationAcceptance } from "./employment_separation_acceptance_contract.mjs";
import { validatePinnedK6AcceptanceEvidence } from "./employment_separation_k6_evidence_contract.mjs";
import { parseRuntimeEvidenceArtifact } from "./employment_separation_runtime_evidence_artifact.mjs";
import { validateRunnerResultDigest } from "./employment_separation_runner_result_digest.mjs";

async function main() {
  const [resultPath, runtimeEvidencePath, fixturePath, runnerResultSha256] = process.argv.slice(2);
  if (!resultPath || !runtimeEvidencePath || !fixturePath || !runnerResultSha256 || process.argv.length !== 6) {
    throw new Error("usage: node employment_separation_acceptance_check.mjs <performance-result.json> <runtime-evidence.json> <performance-fixture.json> <runner-result-sha256>");
  }
  const [resultBytes, runtimeBytes, fixtureBytes] = await Promise.all([
    readFile(resultPath),
    readFile(runtimeEvidencePath),
    readFile(fixturePath),
  ]);
  const verifiedRunnerResultSha256 = validateRunnerResultDigest(resultBytes, runnerResultSha256);
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
    runner_result_sha256: verifiedRunnerResultSha256,
    runtime_evidence_sha256: runtimeDocument.sha256,
  }, null, 2)}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
