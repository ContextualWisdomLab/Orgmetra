import { TextDecoder } from "node:util";

import {
  PINNED_K6_IMAGE,
  PINNED_K6_IMAGE_DIGEST,
  PINNED_K6_RUNNER_IDENTITY,
  PINNED_K6_VERSION,
  requirePinnedK6Runtime,
} from "./employment_separation_k6_runtime_contract.mjs";

function fail(message) { throw new Error(message); }

function parseResultBytes(value) {
  if (!(value instanceof Uint8Array) && !(value instanceof ArrayBuffer)) fail("performance result must be supplied as raw bytes");
  const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
  let text;
  try { text = new TextDecoder("utf-8", { fatal: true }).decode(bytes); }
  catch (error) { throw new Error("performance result must be valid UTF-8", { cause: error }); }
  let result;
  try { result = JSON.parse(text); }
  catch (error) { throw new Error("performance result must be valid JSON", { cause: error }); }
  if (result === null || typeof result !== "object" || Array.isArray(result)) fail("performance result must be an object");
  return result;
}

function runtimeField(runtime, name) {
  if (runtime === null || typeof runtime !== "object" || Array.isArray(runtime)) fail("runtime evidence must be an object");
  const value = runtime[name];
  if (typeof value !== "string" || value === "") fail(`runtime.${name} must be a non-empty string`);
  return value;
}

export function validatePinnedK6AcceptanceEvidence(resultArtifact, runtimeEvidence) {
  const result = parseResultBytes(resultArtifact);
  const resultRuntime = requirePinnedK6Runtime({
    version: result.k6_version,
    image: result.k6_image,
    imageDigest: result.k6_image_digest,
    runnerIdentity: result.k6_runner_identity,
  });
  const observedRuntime = requirePinnedK6Runtime({
    version: runtimeField(runtimeEvidence, "observed_k6_version"),
    image: runtimeField(runtimeEvidence, "observed_k6_image"),
    imageDigest: runtimeField(runtimeEvidence, "observed_k6_image_digest"),
    runnerIdentity: runtimeField(runtimeEvidence, "observed_k6_runner_identity"),
  });
  for (const field of ["version", "image", "image_digest", "runner_identity"]) {
    if (resultRuntime[field] !== observedRuntime[field]) fail(`runtime observed k6 ${field} must match the performance result`);
  }
  return Object.freeze({
    k6_version: PINNED_K6_VERSION,
    k6_image: PINNED_K6_IMAGE,
    k6_image_digest: PINNED_K6_IMAGE_DIGEST,
    k6_runner_identity: PINNED_K6_RUNNER_IDENTITY,
  });
}
