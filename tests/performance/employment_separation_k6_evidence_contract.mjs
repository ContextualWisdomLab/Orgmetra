import { TextDecoder } from "node:util";

import {
  PINNED_K6_RELEASE_ASSET,
  PINNED_K6_RELEASE_ASSET_SHA256,
  PINNED_K6_RUNNER_IDENTITY,
  PINNED_K6_VERSION,
  requirePinnedK6Runtime,
} from "./employment_separation_k6_runtime_contract.mjs";

function fail(message) {
  throw new Error(message);
}

function parseResultBytes(value) {
  if (!(value instanceof Uint8Array) && !(value instanceof ArrayBuffer)) {
    fail("performance result must be supplied as raw bytes");
  }
  const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
  let text;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch (error) {
    throw new Error("performance result must be valid UTF-8", { cause: error });
  }
  let result;
  try {
    result = JSON.parse(text);
  } catch (error) {
    throw new Error("performance result must be valid JSON", { cause: error });
  }
  if (result === null || typeof result !== "object" || Array.isArray(result)) {
    fail("performance result must be an object");
  }
  return result;
}

function runtimeField(runtime, name) {
  if (runtime === null || typeof runtime !== "object" || Array.isArray(runtime)) {
    fail("runtime evidence must be an object");
  }
  const value = runtime[name];
  if (typeof value !== "string" || value === "") {
    fail(`runtime.${name} must be a non-empty string`);
  }
  return value;
}

export function validatePinnedK6AcceptanceEvidence(resultArtifact, runtimeEvidence) {
  const result = parseResultBytes(resultArtifact);
  const resultRuntime = requirePinnedK6Runtime({
    version: result.k6_version,
    releaseAsset: result.k6_release_asset,
    releaseAssetSha256: result.k6_release_asset_sha256,
    runnerIdentity: result.k6_runner_identity,
    executableSha256: result.k6_executable_sha256,
  });
  const observedRuntime = requirePinnedK6Runtime({
    version: runtimeField(runtimeEvidence, "observed_k6_version"),
    releaseAsset: runtimeField(runtimeEvidence, "observed_k6_release_asset"),
    releaseAssetSha256: runtimeField(runtimeEvidence, "observed_k6_release_asset_sha256"),
    runnerIdentity: runtimeField(runtimeEvidence, "observed_k6_runner_identity"),
    executableSha256: runtimeField(runtimeEvidence, "observed_k6_executable_sha256"),
  });
  for (const field of ["version", "release_asset", "release_asset_sha256", "runner_identity", "executable_sha256"]) {
    if (resultRuntime[field] !== observedRuntime[field]) {
      fail(`runtime observed k6 ${field} must match the performance result`);
    }
  }
  return Object.freeze({
    k6_version: PINNED_K6_VERSION,
    k6_release_asset: PINNED_K6_RELEASE_ASSET,
    k6_release_asset_sha256: PINNED_K6_RELEASE_ASSET_SHA256,
    k6_runner_identity: PINNED_K6_RUNNER_IDENTITY,
    k6_executable_sha256: resultRuntime.executable_sha256,
  });
}
