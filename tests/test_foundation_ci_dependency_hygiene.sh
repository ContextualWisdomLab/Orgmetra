#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workflow_path="${repository_root}/.github/workflows/foundation-ci.yml"
requirements_path="${repository_root}/.github/requirements/foundation-test.txt"
node_validator_path="${repository_root}/scripts/foundation-contract-core.mjs"
python_validator_path="${repository_root}/tests/validate_repository.py"
manifest_path="${repository_root}/manifest.json"

expected_install="python -m pip install --require-hashes --no-deps --only-binary=:all: -r .github/requirements/foundation-test.txt"
expected_pythonpath="PYTHONPATH: packages/hris-kernel/src:packages/keyverse-adapter/src"

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

for governed_path in ".github/requirements/foundation-test.txt" "tests/test_foundation_ci_dependency_hygiene.sh"; do
  if ! grep -Fq -- "'${governed_path}'" "${node_validator_path}"; then
    printf 'Node foundation artifact inventory does not govern %s.\n' "${governed_path}" >&2
    exit 1
  fi
  if ! grep -Fq -- "\"${governed_path}\"" "${python_validator_path}"; then
    printf 'Python foundation artifact inventory does not govern %s.\n' "${governed_path}" >&2
    exit 1
  fi
  if ! grep -Fq -- "\"path\": \"${governed_path}\"" "${manifest_path}"; then
    printf 'Deterministic manifest does not seal %s.\n' "${governed_path}" >&2
    exit 1
  fi
done
