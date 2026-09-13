export const PINNED_K6_VERSION = "2.2.0";
export const PINNED_K6_IMAGE = "ghcr.io/grafana/k6";
export const PINNED_K6_IMAGE_DIGEST = "sha256:9bd01d6941fca969cb61bb57d2da5ee9b385fe2aa8881df3798c196564d6ace6";
export const PINNED_K6_RUNNER_IDENTITY = `${PINNED_K6_IMAGE}@${PINNED_K6_IMAGE_DIGEST}`;

export function requirePinnedK6Version(value) {
  if (value !== PINNED_K6_VERSION) {
    throw new Error(`commercial Employment separation performance runs require k6 ${PINNED_K6_VERSION}`);
  }
  return value;
}

export function requirePinnedK6Runtime({ version, image, imageDigest, runnerIdentity }) {
  requirePinnedK6Version(version);
  if (image !== PINNED_K6_IMAGE) {
    throw new Error(`commercial Employment separation performance runs require ${PINNED_K6_IMAGE}`);
  }
  if (imageDigest !== PINNED_K6_IMAGE_DIGEST) {
    throw new Error("commercial Employment separation performance runs require the pinned upstream k6 OCI image digest");
  }
  if (runnerIdentity !== PINNED_K6_RUNNER_IDENTITY) {
    throw new Error("commercial Employment separation performance runs require the pinned upstream k6 OCI runner identity");
  }
  return Object.freeze({
    version,
    image,
    image_digest: imageDigest,
    runner_identity: runnerIdentity,
  });
}
