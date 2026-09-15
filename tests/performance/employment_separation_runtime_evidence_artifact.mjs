import { createHash } from "node:crypto";
import { TextDecoder } from "node:util";

import { parseStrictJsonText } from "./strict_json_artifact.mjs";

function rawBytes(value) {
  if (value instanceof Uint8Array) return value;
  if (value instanceof ArrayBuffer) return new Uint8Array(value);
  throw new Error("runtime evidence must be supplied as raw bytes");
}

export function parseRuntimeEvidenceArtifact(value) {
  const bytes = rawBytes(value);
  let text;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch (error) {
    throw new Error("runtime evidence must be valid UTF-8", { cause: error });
  }

  if (text.trim() === "") {
    throw new Error("runtime evidence must be non-empty JSON text");
  }

  const parsed = parseStrictJsonText(text, "runtime evidence");
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("runtime evidence must be a JSON object");
  }

  return {
    parsed,
    sha256: createHash("sha256").update(bytes).digest("hex"),
  };
}
