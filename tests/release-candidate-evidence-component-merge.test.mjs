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

test('exact internal Python dependency merges into its local component', () => {
  const probe = runBuilderProbe(`
import importlib.util
import json
import sys
spec = importlib.util.spec_from_file_location("orgmetra_release_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

local_project = b'''[project]\nname = "shared-lib"\nversion = "1.0.0"\n'''
consumer_project = b'''[project]\nname = "consumer"\nversion = "1.0.0"\ndependencies = ["shared-lib==1.0.0"]\n'''
sbom = json.loads(module._build_sbom("a" * 40, "b" * 64, {
    "a-shared/pyproject.toml": local_project,
    "z-consumer/pyproject.toml": consumer_project,
}))
shared = [
    component
    for component in sbom["components"]
    if component["bom-ref"] == "pkg:pypi/shared-lib@1.0.0"
]
assert len(shared) == 1
assert shared[0]["scope"] == "required"
assert {tuple(prop.values()) for prop in shared[0]["properties"]} == {
    ("orgmetra:declared-requirement", "shared-lib==1.0.0"),
    ("orgmetra:source:path", "a-shared/pyproject.toml"),
}
consumer_ref = "pkg:pypi/consumer@1.0.0"
consumer_edge = next(row for row in sbom["dependencies"] if row["ref"] == consumer_ref)
assert "pkg:pypi/shared-lib@1.0.0" in consumer_edge["dependsOn"]
`);
  assert.equal(probe.status, 0, probe.stderr || probe.stdout);
});

test('PEP 503-equivalent Python dependency names merge without identity conflict', () => {
  const probe = runBuilderProbe(`
import importlib.util
import json
import sys
spec = importlib.util.spec_from_file_location("orgmetra_release_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

underscore_owner = b'''[project]\nname = "underscore-owner"\nversion = "1.0.0"\ndependencies = ["Foo_Bar==1.0"]\n'''
hyphen_owner = b'''[project]\nname = "hyphen-owner"\nversion = "1.0.0"\ndependencies = ["foo-bar==1.0"]\n'''
sbom = json.loads(module._build_sbom("a" * 40, "b" * 64, {
    "a-underscore/pyproject.toml": underscore_owner,
    "z-hyphen/pyproject.toml": hyphen_owner,
}))
shared = [
    component
    for component in sbom["components"]
    if component["bom-ref"] == "pkg:pypi/foo-bar@1.0"
]
assert len(shared) == 1
declarations = sorted(
    prop["value"]
    for prop in shared[0]["properties"]
    if prop["name"] == "orgmetra:declared-requirement"
)
assert declarations == ["Foo_Bar==1.0", "foo-bar==1.0"]
`);
  assert.equal(probe.status, 0, probe.stderr || probe.stdout);
});

test('exact internal npm dependency retains the local application component type', () => {
  const probe = runBuilderProbe(`
import importlib.util
import json
import sys
spec = importlib.util.spec_from_file_location("orgmetra_release_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

root_package = b'{"name":"orgmetra-root","version":"1.0.0"}'
child_package = b'{"name":"orgmetra-child","version":"1.0.0","dependencies":{"orgmetra-root":"1.0.0"}}'
sbom = json.loads(module._build_sbom("a" * 40, "b" * 64, {
    "package.json": root_package,
    "packages/child/package.json": child_package,
}))
root_ref = "pkg:npm/orgmetra-root@1.0.0"
root = [component for component in sbom["components"] if component["bom-ref"] == root_ref]
assert len(root) == 1
assert root[0]["type"] == "application"
assert root[0]["scope"] == "required"
assert {tuple(prop.values()) for prop in root[0]["properties"]} == {
    ("orgmetra:declared-requirement", "1.0.0"),
    ("orgmetra:source:path", "package.json"),
}
child_edge = next(
    row for row in sbom["dependencies"]
    if row["ref"] == "pkg:npm/orgmetra-child@1.0.0"
)
assert root_ref in child_edge["dependsOn"]
`);
  assert.equal(probe.status, 0, probe.stderr || probe.stdout);
});

test('scoped npm dependency uses canonical namespace and name purl segments', () => {
  const probe = runBuilderProbe(`
import importlib.util
import json
import sys
spec = importlib.util.spec_from_file_location("orgmetra_release_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

owner_package = b'{"name":"owner","version":"1.0.0","dependencies":{"@scope/name":"1.2.3"}}'
sbom = json.loads(module._build_sbom("a" * 40, "b" * 64, {
    "package.json": owner_package,
}))
scoped = [component for component in sbom["components"] if component["name"] == "@scope/name"]
assert len(scoped) == 1
assert scoped[0]["bom-ref"] == "pkg:npm/%40scope/name@1.2.3"
assert scoped[0]["purl"] == "pkg:npm/%40scope/name@1.2.3"
`);
  assert.equal(probe.status, 0, probe.stderr || probe.stdout);
});
