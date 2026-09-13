#!/usr/bin/env bash
set -euo pipefail

readonly PINNED_K6_VERSION="2.2.0"
readonly PINNED_K6_RELEASE_ASSET="k6-v2.2.0-linux-amd64.tar.gz"
readonly PINNED_K6_RELEASE_ASSET_SHA256="b5a8003c86f35f5cd5ceef1490312c48e587696c94d998cefc6d7b3b4cb1597d"
readonly PINNED_K6_RUNNER_IDENTITY="upstream_release_archive:${PINNED_K6_RELEASE_ASSET}@sha256:${PINNED_K6_RELEASE_ASSET_SHA256}"
readonly WORKLOAD="tests/performance/employment_separation_buyer_path.js"

archive="${ORGMETRA_K6_RELEASE_ARCHIVE:-}"
if [[ -z "${archive}" || ! -f "${archive}" ]]; then
  printf 'ORGMETRA_K6_RELEASE_ARCHIVE must point to the pinned upstream release archive\n' >&2
  exit 1
fi
if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
  printf 'commercial Employment separation performance runner requires Linux x86_64 for %s\n' "${PINNED_K6_RELEASE_ASSET}" >&2
  exit 1
fi
if ! command -v sha256sum >/dev/null 2>&1 || ! command -v tar >/dev/null 2>&1; then
  printf 'sha256sum and tar are required to verify the pinned k6 release artifact\n' >&2
  exit 1
fi

tmp_root="$(mktemp -d)"
trap 'rm -rf -- "${tmp_root}"' EXIT HUP INT TERM
archive_copy="${tmp_root}/${PINNED_K6_RELEASE_ASSET}"
cp -- "${archive}" "${archive_copy}"
observed_archive_sha256="$(sha256sum "${archive_copy}" | awk '{print $1}')"
if [[ "${observed_archive_sha256}" != "${PINNED_K6_RELEASE_ASSET_SHA256}" ]]; then
  printf 'k6 release archive SHA-256 mismatch: expected %s, observed %s\n' \
    "${PINNED_K6_RELEASE_ASSET_SHA256}" "${observed_archive_sha256}" >&2
  exit 1
fi

extract_root="${tmp_root}/extract"
mkdir -p "${extract_root}"
tar -xzf "${archive_copy}" -C "${extract_root}"
mapfile -t k6_candidates < <(find "${extract_root}" -type f -name k6 -perm -u+x -print)
if [[ "${#k6_candidates[@]}" -ne 1 ]]; then
  printf 'verified k6 archive must contain exactly one executable named k6; found %s\n' "${#k6_candidates[@]}" >&2
  exit 1
fi
k6_bin="${k6_candidates[0]}"
observed_executable_sha256="$(sha256sum "${k6_bin}" | awk '{print $1}')"
version_line="$(${k6_bin} version 2>&1 | head -n 1)"
version_token="$(printf '%s\n' "${version_line}" | awk '{print $2}')"
if [[ "${version_token}" != "v${PINNED_K6_VERSION}" ]]; then
  printf 'verified release archive must contain k6 v%s; observed: %s\n' \
    "${PINNED_K6_VERSION}" "${version_line}" >&2
  exit 1
fi

export ORGMETRA_PERFORMANCE_K6_VERSION="${PINNED_K6_VERSION}"
export ORGMETRA_PERFORMANCE_K6_RELEASE_ASSET="${PINNED_K6_RELEASE_ASSET}"
export ORGMETRA_PERFORMANCE_K6_RELEASE_ASSET_SHA256="${PINNED_K6_RELEASE_ASSET_SHA256}"
export ORGMETRA_PERFORMANCE_K6_RUNNER_IDENTITY="${PINNED_K6_RUNNER_IDENTITY}"
export ORGMETRA_PERFORMANCE_K6_EXECUTABLE_SHA256="${observed_executable_sha256}"
"${k6_bin}" run "${WORKLOAD}" "$@"
