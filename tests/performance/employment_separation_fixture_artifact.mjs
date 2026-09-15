import { parseStrictJsonText } from "./strict_json_artifact.mjs";

export const MAXIMUM_PERFORMANCE_FIXTURE_BYTES = 8 * 1024 * 1024;

export function requirePerformanceFixtureByteBudget(value) {
  if (!(value instanceof Uint8Array) && !(value instanceof ArrayBuffer)) {
    throw new Error("performance fixture must be supplied as raw bytes");
  }
  if (value.byteLength > MAXIMUM_PERFORMANCE_FIXTURE_BYTES) {
    throw new Error(`performance fixture must not exceed ${MAXIMUM_PERFORMANCE_FIXTURE_BYTES} bytes`);
  }
  return value;
}

export function parsePerformanceFixtureArtifact(value) {
  const bytes = requirePerformanceFixtureByteBudget(value);
  let text;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch (error) {
    throw new Error("performance fixture must be valid UTF-8", { cause: error });
  }
  if (text.trim() === "") {
    throw new Error("performance fixture must be non-empty JSON text");
  }
  return parseStrictJsonText(text, "performance fixture");
}
