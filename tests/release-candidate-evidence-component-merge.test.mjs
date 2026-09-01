import assert from 'node:assert/strict';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const builderPath = join(repoRoot, 'scripts', 'build-release-candidate-evidence.py');

function runBuilderProbe(program) {
  return spawnSync('python', ['-c', program, builderPath], {
    cwd: repoRoot,
    encoding: 'utf8',
  });
}

test('equivalent Python pins merge declaration evidence and strongest CycloneDX scope', () => {
  const probe = runBuilderProbe(`
import importlib.util
import json
import sys
spec = importlib.util.spec_from_file_location("orgmetra_release_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

optional_project = b'''[project]\nname = "optional-owner"\nversion = "1.0.0"\n\n[project.optional-dependencies]\ntest = ["shared==v1.0"]\n'''
required_project = b'''[project]\nname = "required-owner"\nversion = "1.0.0"\ndependencies = ["shared==1.0"]\n'''

def shared_component(tree):
    sbom = json.loads(module._build_sbom("a" * 40, "b" * 64, tree))
    matches = [component for component in sbom["components"] if component["name"] == "shared"]
    assert len(matches) == 1
    return matches[0]

optional_first = shared_component({
    "a-optional/pyproject.toml": optional_project,
    "z-required/pyproject.toml": required_project,
})
required_first = shared_component({
    "a-required/pyproject.toml": required_project,
    "z-optional/pyproject.toml": optional_project,
})

for component in (optional_first, required_first):
    assert component["bom-ref"] == "pkg:pypi/shared@1.0"
    assert component["scope"] == "required"
    declarations = sorted(
        prop["value"]
        for prop in component["properties"]
        if prop["name"] == "orgmetra:declared-requirement"
    )
    assert declarations == ["shared==1.0", "shared==v1.0"]
`);
  assert.equal(probe.status, 0, probe.stderr || probe.stdout);
});
