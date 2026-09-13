import { createHash } from "node:crypto";

const SHA256_PATTERN = /^[0-9a-f]{64}$/;

function rawBytes(value) {
  if (value instanceof Uint8Array) return value;
  if (value instanceof ArrayBuffer) return new Uint8Array(value);
  throw new Error("performance result must be supplied as raw bytes");
}

export function validateRunnerResultDigest(resultArtifact, expectedDigest) {
  if (typeof expectedDigest !== "string" || !SHA256_PATTERN.test(expectedDigest)) {
    throw new Error("runner result digest must be a SHA-256 digest");
  }
  const bytes = rawBytes(resultArtifact);
  const actualDigest = createHash("sha256").update(bytes).digest("hex");
  if (actualDigest !== expectedDigest) {
    throw new Error("runner result digest does not bind the supplied performance result");
  }
  return actualDigest;
}
