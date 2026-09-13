#!/usr/bin/env bash
set -euo pipefail

readonly PINNED_K6_VERSION="2.2.0"
readonly PINNED_K6_IMAGE="ghcr.io/grafana/k6"
readonly PINNED_K6_IMAGE_DIGEST="sha256:9bd01d6941fca969cb61bb57d2da5ee9b385fe2aa8881df3798c196564d6ace6"
readonly PINNED_K6_RUNNER_IDENTITY="${PINNED_K6_IMAGE}@${PINNED_K6_IMAGE_DIGEST}"
readonly WORKLOAD="/workspace/tests/performance/employment_separation_buyer_path.js"

if (( $# != 0 )); then
  printf 'commercial Employment separation benchmark does not accept caller-supplied k6 CLI options\n' >&2
  exit 64
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
target_sha="${ORGMETRA_PERFORMANCE_TARGET_SHA:-}"
if [[ ! "${target_sha}" =~ ^[0-9a-f]{40}$ ]]; then
  printf 'ORGMETRA_PERFORMANCE_TARGET_SHA must be the exact lowercase 40-character candidate SHA\n' >&2
  exit 1
fi
repository_head="$(git -C "${repo_root}" rev-parse --verify HEAD)"
if [[ "${repository_head}" != "${ORGMETRA_PERFORMANCE_TARGET_SHA}" ]]; then
  printf 'benchmark checkout HEAD must equal ORGMETRA_PERFORMANCE_TARGET_SHA; head=%s target=%s\n' "${repository_head}" "${ORGMETRA_PERFORMANCE_TARGET_SHA}" >&2
  exit 1
fi
repository_status="$(git -C "${repo_root}" status --porcelain=v1 --untracked-files=all)"
if [[ -n "${repository_status}" ]]; then
  printf 'commercial performance evidence requires an exact clean checkout; modified, staged, or untracked files are present\n' >&2
  exit 1
fi

if ! command -v podman >/dev/null 2>&1; then
  printf 'podman is required for the pinned commercial k6 runner\n' >&2
  exit 1
fi
if ! podman image exists "${PINNED_K6_RUNNER_IDENTITY}"; then
  printf 'preload the exact pinned k6 image before measurement: %s\n' "${PINNED_K6_RUNNER_IDENTITY}" >&2
  exit 1
fi
version_line="$(podman run --rm --pull=never "${PINNED_K6_RUNNER_IDENTITY}" version 2>&1 | head -n 1)"
version_token="$(printf '%s\n' "${version_line}" | awk '{print $2}')"
if [[ "${version_token}" != "v${PINNED_K6_VERSION}" ]]; then
  printf 'pinned k6 image must report v%s; observed: %s\n' "${PINNED_K6_VERSION}" "${version_line}" >&2
  exit 1
fi

fixture_path="${ORGMETRA_PERFORMANCE_DATA_FILE:-}"
summary_path="${ORGMETRA_PERFORMANCE_SUMMARY_FILE:-}"
if [[ -z "${fixture_path}" || ! -f "${fixture_path}" ]]; then
  printf 'ORGMETRA_PERFORMANCE_DATA_FILE must point to the right-cleared fixture\n' >&2
  exit 1
fi
if [[ -z "${summary_path}" ]]; then
  printf 'ORGMETRA_PERFORMANCE_SUMMARY_FILE is required\n' >&2
  exit 1
fi
fixture_path="$(realpath "${fixture_path}")"
summary_dir="$(realpath -m "$(dirname "${summary_path}")")"
summary_name="$(basename "${summary_path}")"
mkdir -p "${summary_dir}"

export ORGMETRA_PERFORMANCE_K6_VERSION="${PINNED_K6_VERSION}"
export ORGMETRA_PERFORMANCE_K6_IMAGE="${PINNED_K6_IMAGE}"
export ORGMETRA_PERFORMANCE_K6_IMAGE_DIGEST="${PINNED_K6_IMAGE_DIGEST}"
export ORGMETRA_PERFORMANCE_K6_RUNNER_IDENTITY="${PINNED_K6_RUNNER_IDENTITY}"

podman run --rm --pull=never --network=host --read-only \
  --cap-drop=ALL --security-opt=no-new-privileges --pids-limit=256 \
  --tmpfs /tmp:rw,nosuid,nodev,noexec \
  --volume "${repo_root}:/workspace:ro" \
  --volume "${fixture_path}:/evidence/fixture.json:ro" \
  --volume "${summary_dir}:/output:rw" \
  --workdir /workspace \
  --env ORGMETRA_PERFORMANCE_BASE_URL \
  --env ORGMETRA_PERFORMANCE_BEARER_TOKEN \
  --env ORGMETRA_PERFORMANCE_TARGET_SHA \
  --env ORGMETRA_PERFORMANCE_PROFILE \
  --env ORGMETRA_PERFORMANCE_K6_VERSION \
  --env ORGMETRA_PERFORMANCE_K6_IMAGE \
  --env ORGMETRA_PERFORMANCE_K6_IMAGE_DIGEST \
  --env ORGMETRA_PERFORMANCE_K6_RUNNER_IDENTITY \
  --env ORGMETRA_PERFORMANCE_DATA_FILE=/evidence/fixture.json \
  --env "ORGMETRA_PERFORMANCE_SUMMARY_FILE=/output/${summary_name}" \
  "${PINNED_K6_RUNNER_IDENTITY}" run "${WORKLOAD}"
