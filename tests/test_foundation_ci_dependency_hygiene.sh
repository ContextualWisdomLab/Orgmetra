#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workflow_path="${repository_root}/.github/workflows/foundation-ci.yml"
requirements_path="${repository_root}/.github/requirements/foundation-test.txt"

expected_install="python -m pip install --require-hashes --no-deps --only-binary=:all: -r .github/requirements/foundation-test.txt"
expected_pythonpath="PYTHONPATH: packages/hris-kernel/src:packages/keyverse-adapter/src"
expected_default_pr_target=$'  pull_request:\n    branches:\n      - develop\n'

if ! grep -Fq -- "${expected_install}" "${workflow_path}"; then
  printf 'Foundation CI must install only the hash-locked test toolchain.\n' >&2
  exit 1
fi

if grep -Eq -- 'python -m pip install .*packages/' "${workflow_path}"; then
  printf 'Foundation CI must not build/install repository-local packages into the checkout.\n' >&2
  exit 1
fi

if ! grep -Fq -- "${expected_pythonpath}" "${workflow_path}"; then
  printf 'Foundation CI must import repository-local packages directly from their src trees.\n' >&2
  exit 1
fi

if ! grep -Fq -- "${expected_default_pr_target}" "${workflow_path}"; then
  printf 'Foundation CI must run for pull requests targeting the repository default branch develop.\n' >&2
  exit 1
fi

mapfile -t pull_request_branches < <(
  awk '
    /^  pull_request:/ { in_pull_request=1; next }
    in_pull_request && /^  [[:alnum:]_-]+:/ { exit }
    in_pull_request && /^      - / {
      sub(/^      - /, "")
      print
    }
  ' "${workflow_path}"
)

if [[ "${#pull_request_branches[@]}" -eq 0 ]]; then
  printf 'Foundation CI must declare pull_request target branches.\n' >&2
  exit 1
fi

duplicate_pull_request_branches="$(
  printf '%s\n' "${pull_request_branches[@]}" | sort | uniq -d
)"
if [[ -n "${duplicate_pull_request_branches}" ]]; then
  printf 'Foundation CI pull_request branches must be unique: %s\n' "${duplicate_pull_request_branches}" >&2
  exit 1
fi

if [[ ! -f "${requirements_path}" ]]; then
  printf 'Hash-locked Foundation CI requirements are missing.\n' >&2
  exit 1
fi

mapfile -t package_lines < <(grep -Ev '^[[:space:]]*(#|$)' "${requirements_path}")
if [[ "${#package_lines[@]}" -ne 7 ]]; then
  printf 'Foundation CI requirements must contain the seven reviewed direct/runtime test packages.\n' >&2
  exit 1
fi

for package_line in "${package_lines[@]}"; do
  if [[ ! "${package_line}" =~ ^[A-Za-z0-9._-]+==[0-9][A-Za-z0-9._-]*[[:space:]]--hash=sha256:[0-9a-f]{64}$ ]]; then
    printf 'Unpinned or unhashed Foundation CI requirement: %s\n' "${package_line}" >&2
    exit 1
  fi
done

for package_name in coverage iniconfig packaging pluggy Pygments pytest pytest-cov; do
  if ! printf '%s\n' "${package_lines[@]}" | grep -Eq "^${package_name}=="; then
    printf 'Foundation CI requirement is missing: %s\n' "${package_name}" >&2
    exit 1
  fi
done
