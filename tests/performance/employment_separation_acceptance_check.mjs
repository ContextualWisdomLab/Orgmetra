import { readFile } from "node:fs/promises";

import { validateEmploymentSeparationAcceptance } from "./employment_separation_acceptance_contract.mjs";
import { requireCommercialPerformanceAuthorities } from "./employment_separation_commercial_owner_gate.mjs";
import { validatePinnedK6AcceptanceEvidence } from "./employment_separation_k6_evidence_contract.mjs";
import { parseRuntimeEvidenceArtifact } from "./employment_separation_runtime_evidence_artifact.mjs";

async function main() {
  // Byte/provenance attestation and deployed-candidate identity are separate
  // trust boundaries. Surface every unresolved owner gap before touching caller
  // paths so resolving one authority cannot accidentally enable acceptance while
  // the other remains self-asserted.
  requireCommercialPerformanceAuthorities();

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
  const evidenceContract = validateEmploymentSeparationAcceptance(
    resultBytes,
    runtimeDocument.parsed,
    fixtureBytes,
  );
  // Structural validation owns the bounded/strict result parser. Run it before
  // this secondary pinned-runtime interpretation so duplicate members, nesting
  // abuse, and oversized result artifacts cannot reach ordinary JSON.parse first.
  const k6Evidence = validatePinnedK6AcceptanceEvidence(resultBytes, runtimeDocument.parsed);
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
