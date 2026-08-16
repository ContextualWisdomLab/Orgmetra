import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import test from 'node:test';
import {
  DATABASE_OBJECT_NAMES,
  MATURITY_VALUES,
  REQUIRED_FILES,
  collectMarkdownFiles,
  countCodeFences,
  extractMaturityCells,
  extractSection,
  isValidDatabaseObjectName,
  runCli,
  validateAdrIndex,
  validateDatabaseObjectNames,
  validateFoundation,
  validateLocalLinks
} from '../scripts/foundation-contract-core.mjs';

function temporaryDirectory() {
  return mkdtempSync(join(tmpdir(), 'orgmetra-foundation-'));
}

function write(root, relativePath, content = '# Valid\n') {
  const filePath = join(root, relativePath);
  mkdirSync(dirname(filePath), { recursive: true });
  writeFileSync(filePath, content, 'utf8');
  return filePath;
}

function pythonRequiredFiles() {
  const source = readFileSync(new URL('./validate_repository.py', import.meta.url), 'utf8');
  const match = source.match(/REQUIRED = \[(.*?)\]\n\n/s);
  assert.ok(match, 'Python REQUIRED list was not found');
  return [...match[1].matchAll(/^\s+"([^"]+)",$/gm)].map((item) => item[1]);
}

function makeMinimalValidFoundation(root) {
  for (const filePath of REQUIRED_FILES) write(root, filePath);
  write(
    root,
    'schemas/openapi.yaml',
    readFileSync(new URL('../schemas/openapi.yaml', import.meta.url), 'utf8')
  );
  write(
    root,
    'docs/TRACEABILITY.md',
    '# Traceability\n\n## 2. Product traceability matrix\n\n| Requirement | Current maturity |\n|---|---|\n| Temporal | accepted_architecture |\n\n## 3. Standards\n\nText.\n\n## 4. CWL integration traceability\n\n| Product | Maturity |\n|---|---|\n| Keyverse | planned |\n\n## 5. Evidence\n'
  );
  write(
    root,
    'docs/adr/README.md',
    '# ADRs\n\n| ADR | Title | Status |\n|---|---|---|\n| [0001](0001-orgmetra-authoritative-hris-record.md) | Core | Accepted |\n| [0002](0002-federated-cwl-integration-boundaries.md) | Federation | Accepted |\n| [0003](0003-bitemporal-hris-data-contract.md) | Time | Accepted |\n'
  );
  write(root, 'docs/adr/0001-orgmetra-authoritative-hris-record.md', '# ADR\n\nStatus: Accepted\n');
  write(root, 'docs/adr/0002-federated-cwl-integration-boundaries.md', '# ADR\n\nStatus: Accepted\n');
  write(root, 'docs/adr/0003-bitemporal-hris-data-contract.md', '# ADR\n\nStatus: Accepted\n');
}

function memoryStream() {
  let text = '';
  return {
    write(chunk) {
      text += chunk;
    },
    value() {
      return text;
    }
  };
}

test('canonical foundation passes validation', () => {
  assert.deepEqual(validateFoundation(resolve('.')), []);
});

test('Python and Node require the identical foundation artifact set', () => {
  assert.deepEqual([...REQUIRED_FILES].sort(), pythonRequiredFiles().sort());
});

test('required constants are frozen and use accepted values', () => {
  assert.equal(Object.isFrozen(REQUIRED_FILES), true);
  assert.equal(Object.isFrozen(DATABASE_OBJECT_NAMES), true);
  assert.equal(Object.isFrozen(MATURITY_VALUES), true);
  assert.ok(REQUIRED_FILES.length > 20);
  assert.ok(DATABASE_OBJECT_NAMES.every(isValidDatabaseObjectName));
  assert.ok(MATURITY_VALUES.has('accepted_architecture'));
});

test('collectMarkdownFiles handles missing directories and stable recursion', () => {
  const root = temporaryDirectory();
  try {
    assert.deepEqual(collectMarkdownFiles(join(root, 'missing')), []);
    write(root, 'z.md');
    write(root, 'a/readme.md');
    write(root, 'a/not-markdown.txt');
    assert.deepEqual(
      collectMarkdownFiles(root).map((filePath) => filePath.slice(root.length + 1)),
      ['a/readme.md', 'z.md']
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('Markdown helpers count fences and extract bounded sections', () => {
  assert.equal(countCodeFences('# A\n```text\nx\n```\n'), 2);
  assert.equal(countCodeFences('no fence'), 0);
  const markdown = '# T\n\n## Alpha\nA\n\n## Beta\nB\n';
  assert.equal(extractSection(markdown, 'Alpha').trim(), 'A');
  assert.equal(extractSection(markdown, 'Beta').trim(), 'B');
  assert.equal(extractSection(markdown, 'Missing'), '');
});

test('extractMaturityCells ignores non-rows, headers, separators, and empty rows', () => {
  const section = 'Text\n| Item | maturity |\n|---|---|\n||\n| A | planned |\n| B | accepted_architecture |\n| prose | Not_a_value |\n';
  assert.deepEqual(extractMaturityCells(section), ['planned', 'accepted_architecture']);
});

test('database naming accepts multiword snake_case and rejects invalid forms', () => {
  assert.equal(isValidDatabaseObjectName('person_record'), true);
  assert.equal(isValidDatabaseObjectName('person'), false);
  assert.equal(isValidDatabaseObjectName('Person_Record'), false);
  assert.equal(isValidDatabaseObjectName('_person_record'), false);
  assert.equal(isValidDatabaseObjectName('person__record'), false);
  assert.deepEqual(validateDatabaseObjectNames(['person_record']), []);
  assert.deepEqual(
    validateDatabaseObjectNames(['person']),
    ['Invalid database object name: person']
  );
});

test('local links validate files and ignore anchors, web, and mail links', () => {
  const root = temporaryDirectory();
  try {
    const source = write(root, 'docs/source.md');
    write(root, 'docs/target file.md');
    const valid = '[ok](target%20file.md#part) [anchor](#part) [web](https://example.com) [mail](mailto:test@example.com)';
    assert.deepEqual(validateLocalLinks(source, valid), []);
    const errors = validateLocalLinks(source, '[missing](missing.md)');
    assert.equal(errors.length, 1);
    assert.match(errors[0], /missing\.md/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('ADR index reports missing files and status mismatch', () => {
  const root = temporaryDirectory();
  try {
    write(
      root,
      'docs/adr/README.md',
      '# Index\n| Header | Header | Header |\n| [0001](0001.md) | A | Accepted |\n| [0002](missing.md) | B | Proposed |\n'
    );
    write(root, 'docs/adr/0001.md', '# ADR\n\nStatus: Proposed\n');
    const errors = validateAdrIndex(root);
    assert.equal(errors.length, 2);
    assert.ok(errors.some((error) => /status does not match/.test(error)));
    assert.ok(errors.some((error) => /indexed ADR is missing/.test(error)));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('ADR validation is empty when the index is absent', () => {
  const root = temporaryDirectory();
  try {
    assert.deepEqual(validateAdrIndex(root), []);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('foundation validator reports a missing repository root', () => {
  const root = join(tmpdir(), `orgmetra-absent-${Date.now()}`);
  assert.match(validateFoundation(root)[0], /Repository root does not exist/);
});

test('foundation validator reports every missing artifact', () => {
  const root = temporaryDirectory();
  try {
    const errors = validateFoundation(root);
    assert.equal(errors.length, REQUIRED_FILES.length);
    assert.match(errors[0], /Missing required foundation artifact/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('foundation validator reports placeholders, fences, links, and maturities', () => {
  const root = temporaryDirectory();
  try {
    makeMinimalValidFoundation(root);
    write(root, 'README.md', '# TODO\n\n```text\n[missing](not-here.md)\n');
    write(
      root,
      'docs/TRACEABILITY.md',
      '# Trace\n\n## 2. Product traceability matrix\n\n| A | invalid_value |\n\n## 4. CWL integration traceability\n\n| B | invalid_value |\n'
    );
    const errors = validateFoundation(root);
    assert.ok(errors.some((error) => /placeholder/.test(error)));
    assert.ok(errors.some((error) => /code fence/.test(error)));
    assert.ok(errors.some((error) => /local link target/.test(error)));
    assert.equal(errors.filter((error) => /invalid maturity value/.test(error)).length, 2);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('foundation validator reports missing traceability sections', () => {
  const root = temporaryDirectory();
  try {
    makeMinimalValidFoundation(root);
    write(root, 'docs/TRACEABILITY.md', '# Traceability\n');
    const errors = validateFoundation(root);
    assert.equal(errors.filter((error) => /missing section/.test(error)).length, 2);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('minimal valid fixture passes and CLI returns success', () => {
  const root = temporaryDirectory();
  try {
    makeMinimalValidFoundation(root);
    const output = memoryStream();
    const errors = memoryStream();
    assert.deepEqual(validateFoundation(root), []);
    assert.equal(runCli(root, output, errors), 0);
    assert.match(output.value(), /"status":"passed"/);
    assert.equal(errors.value(), '');
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('CLI returns a structured failure report', () => {
  const root = temporaryDirectory();
  try {
    const output = memoryStream();
    const errors = memoryStream();
    assert.equal(runCli(root, output, errors), 1);
    assert.equal(output.value(), '');
    assert.match(errors.value(), /"status": "failed"/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
