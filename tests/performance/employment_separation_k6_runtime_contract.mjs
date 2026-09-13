export const PINNED_K6_VERSION = "2.2.0";
export const PINNED_K6_RELEASE_ASSET = "k6-v2.2.0-linux-amd64.tar.gz";
export const PINNED_K6_RELEASE_ASSET_SHA256 = "b5a8003c86f35f5cd5ceef1490312c48e587696c94d998cefc6d7b3b4cb1597d";
export const PINNED_K6_RUNNER_IDENTITY = `upstream_release_archive:${PINNED_K6_RELEASE_ASSET}@sha256:${PINNED_K6_RELEASE_ASSET_SHA256}`;
const SHA256_PATTERN = /^[0-9a-f]{64}$/;

export function requirePinnedK6Version(value) {
  if (value !== PINNED_K6_VERSION) {
    throw new Error(`commercial Employment separation performance runs require k6 ${PINNED_K6_VERSION}`);
  }
  return value;
}

export function requirePinnedK6Runtime({
  version,
  releaseAsset,
  releaseAssetSha256,
  runnerIdentity,
  executableSha256,
}) {
  requirePinnedK6Version(version);
  if (releaseAsset !== PINNED_K6_RELEASE_ASSET) {
    throw new Error(`commercial Employment separation performance runs require ${PINNED_K6_RELEASE_ASSET}`);
  }
  if (releaseAssetSha256 !== PINNED_K6_RELEASE_ASSET_SHA256) {
    throw new Error("commercial Employment separation performance runs require the pinned upstream k6 release-asset SHA-256");
  }
  if (runnerIdentity !== PINNED_K6_RUNNER_IDENTITY) {
    throw new Error("commercial Employment separation performance runs require the pinned upstream k6 runner identity");
  }
  if (typeof executableSha256 !== "string" || !SHA256_PATTERN.test(executableSha256)) {
    throw new Error("commercial Employment separation performance runs require the extracted k6 executable SHA-256");
  }
  return Object.freeze({
    version,
    release_asset: releaseAsset,
    release_asset_sha256: releaseAssetSha256,
    runner_identity: runnerIdentity,
    executable_sha256: executableSha256,
  });
}
