import { readFile } from "node:fs/promises";

import { validateEmploymentSeparationAcceptance } from "./employment_separation_acceptance_contract.mjs";

async function main() {
  const [resultPath, runtimeEvidencePath, fixturePath] = process.argv.slice(2);
  if (!resultPath || !runtimeEvidencePath || !fixturePath || process.argv.length !== 5) {
    throw new Error("usage: node employment_separation_acceptance_check.mjs <performance-result.json> <runtime-evidence.json> <performance-fixture.json>");
  }
  const [resultBytes, runtimeText, fixtureBytes] = await Promise.all([
    readFile(resultPath),
    readFile(runtimeEvidencePath, "utf8"),
    readFile(fixturePath),
  ]);
  let runtimeEvidence;
  try {
    runtimeEvidence = JSON.parse(runtimeText);
  } catch (error) {
    throw new Error("runtime evidence must be valid JSON", { cause: error });
  }
  const acceptance = validateEmploymentSeparationAcceptance(resultBytes, runtimeEvidence, fixtureBytes);
  process.stdout.write(`${JSON.stringify(acceptance, null, 2)}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
