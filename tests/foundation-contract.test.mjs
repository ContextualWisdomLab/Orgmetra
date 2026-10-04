import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import test from 'node:test';
import {
  DATABASE_OBJECT_NAMES,
  MIGRATION_BACKED_DATABASE_OBJECT_NAMES,
  MATURITY_VALUES,
  REQUIRED_FILES,
  collectMarkdownFiles,
  countCodeFences,
  extractMaturityCells,
  extractSection,
  findUnfinishedMarker,
  hasUnfinishedMarker,
  isValidDatabaseObjectName,
  runCli,
  validateAdrIndex,
  validateDatabaseObjectNames,
  validateFoundation,
  validateLocalLinks,
  validateMigrationBackedDatabaseObjectNames
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

function writeMigrationBackedTables(root) {
  write(
    root,
    'database/migrations/0013_job_analysis_snapshot.sql',
    [
      'CREATE TABLE job_analysis_snapshot (tenant_record_id uuid NOT NULL);',
      'CREATE TABLE job_analysis_task_item (tenant_record_id uuid NOT NULL);',
      'CREATE TABLE job_analysis_ksao_item (tenant_record_id uuid NOT NULL);',
      'CREATE TABLE job_analysis_task_ksao_link (tenant_record_id uuid NOT NULL);',
      'CREATE TABLE job_analysis_write_command (tenant_record_id uuid NOT NULL);'
    ].join('\n') + '\n'
  );
}

function makeMinimalValidFoundation(root) {
  for (const filePath of REQUIRED_FILES) write(root, filePath);
  write(
    root,
    'database/migrations/0012_people_mutation_idempotency.sql',
    'CREATE TABLE people_mutation_idempotency_record (tenant_record_id uuid NOT NULL);\n'
  );
  writeMigrationBackedTables(root);
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

test('Job Architecture ownership documents its existing snapshot tables', () => {
  const architecture = readFileSync(new URL('../ARCHITECTURE.md', import.meta.url), 'utf8');
  const migration = readFileSync(new URL('../database/migrations/0013_job_analysis_snapshot.sql', import.meta.url), 'utf8');
  const rows = architecture.split('\n').filter((line) => line.startsWith('| `job_architecture` |'));
  assert.equal(rows.length, 1, 'the owning context must have one representative table row');
  assert.match(rows[0], /job profiles and publication evidence/);
  assert.match(rows[0], /`job_architecture_role`/);
  for (const table of ['job_analysis_snapshot', 'job_analysis_task_item', 'job_analysis_ksao_item']) {
    assert.match(migration, new RegExp(`CREATE TABLE ${table} \\(`), `${table} must exist in the owned migration`);
    assert.ok(rows[0].includes(`\`${table}\``), `${table} must appear in its owning architecture row`);
  }
});

test('workspace documentation separates observed source from historical execution', () => {
  const readme = readFileSync(new URL('../README.md', import.meta.url), 'utf8');
  const gap = readFileSync(new URL('../docs/product-technical-gap-baseline.md', import.meta.url), 'utf8');
  const status = readme.split('## Status\n')[1];
  assert.ok(status, 'README must retain its complete status section');
  assert.match(status, /Observed default `develop` base `eb9757f8649aaad026a9865508d9aad50c1a7a4f`/);
  assert.match(status, /repository source presence only/);
  assert.doesNotMatch(status, /Workforce-composition evidence remains active PR #54/);
  assert.match(gap, /\*\*Historical snapshot:\*\* 2026-08-21, Asia\/Seoul/);
  assert.match(gap, /## Historical open PR inventory and integration order \(2026-08-21\)/);
  assert.match(gap, /## Historical local evidence \(2026-08-21\)/);
  assert.match(gap, /not evidence of configured branch-protection enforcement/);
  assert.match(gap, /No new all-PR inventory is asserted/);
  assert.match(gap, /Historical exact-head service and PostgreSQL validation/);
  assert.match(gap, /parameter_rmse_mean` 2\.9606/);
});

test('offer approval ADR keeps its exact decision status separate from branch provenance', () => {
  const adr = readFileSync(new URL('../docs/adr/0017-governed-offer-approval.md', import.meta.url), 'utf8');
  const index = readFileSync(new URL('../docs/adr/README.md', import.meta.url), 'utf8');
  const statuses = [...adr.matchAll(/^- Status: (.+)$/gm)].map((match) => match[1]);
  assert.deepEqual(statuses, ['Accepted'], 'decision status must not include a branch or protection claim');
  const indexed = index.split('\n').find((line) => line.includes('| [0017]'));
  assert.ok(indexed);
  assert.equal(indexed.split('|').at(-2).trim(), statuses[0]);
  assert.match(adr, /^- Provenance: .*develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f.*configured protection remains a separate gap/m);
  assert.doesNotMatch(adr, /protected `develop` truth|^Protected `develop` can govern/m);
});

test('Job Analysis traceability includes the persisted snapshot and its contract source', () => {
  const traceability = readFileSync(new URL('../docs/TRACEABILITY.md', import.meta.url), 'utf8');
  const migration = readFileSync(new URL('../database/migrations/0013_job_analysis_snapshot.sql', import.meta.url), 'utf8');
  const rows = traceability.split('\n').filter((line) => line.startsWith('| Evidence-grounded Job analysis with Task/FJA/KSAO linkage |'));
  assert.equal(rows.length, 1);
  for (const table of ['job_analysis_snapshot', 'job_analysis_task_item', 'job_analysis_ksao_item', 'job_analysis_task_ksao_link', 'job_analysis_write_command']) {
    assert.match(migration, new RegExp(`CREATE TABLE ${table} \\(`));
    assert.ok(rows[0].includes(`\`${table}\``), `${table} must be traced to its persistence boundary`);
  }
  for (const path of ['services/job-analysis-api', 'tests/test_job_analysis_snapshot_postgres.sh']) {
    assert.ok(rows[0].includes(`\`${path}\``), `${path} must appear in the same evidence row`);
  }
  assert.ok(rows[0].includes('ADR-0007, ADR-0014'));
});

test('governance docs name the protected default branch rather than stale main', () => {
  const agents = readFileSync(new URL('../AGENTS.md', import.meta.url), 'utf8');
  assert.doesNotMatch(agents, /protected[- ](?:`)?main(?:`)?/i);
  assert.match(agents, /protected default branch/i);
});

test('PostgreSQL CI service image is pinned to the approved immutable PostgreSQL 16.14 digest', () => {
  const workflow = readFileSync(
    new URL('../.github/workflows/foundation-ci.yml', import.meta.url),
    'utf8'
  );
  assert.match(
    workflow,
    /ORGMETRA_POSTGRES_IMAGE: postgres:16\.14@sha256:33f923b05f64ca54ac4401c01126a6b92afe839a0aa0a52bc5aeb5cc958e5f20/
  );
  assert.match(workflow, /docker run[\s\S]*"\$ORGMETRA_POSTGRES_IMAGE"/);
  assert.doesNotMatch(workflow, /postgres:16(?:\s|$)/m);
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
  assert.ok(DATABASE_OBJECT_NAMES.includes('people_mutation_idempotency_record'));
  assert.ok(MATURITY_VALUES.has('accepted_architecture'));
});

test('migration-backed database object validation detects table rename', () => {
  const root = temporaryDirectory();
  try {
    write(
      root,
      'database/migrations/0012_people_mutation_idempotency.sql',
      'CREATE TABLE people_mutation_idempotency_record (tenant_record_id uuid NOT NULL);\n'
    );
    writeMigrationBackedTables(root);
    assert.deepEqual(validateMigrationBackedDatabaseObjectNames(root), []);
    write(
      root,
      'database/migrations/0012_people_mutation_idempotency.sql',
      'CREATE TABLE people_mutation_replay_record (tenant_record_id uuid NOT NULL);\n'
    );
    assert.deepEqual(validateMigrationBackedDatabaseObjectNames(root), [
      'Migration-backed database object is missing from migrations: people_mutation_idempotency_record'
    ]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('migration-backed validation ignores fake CREATE TABLE text in comments and literals', () => {
  const root = temporaryDirectory();
  try {
    write(
      root,
      'database/migrations/0012_people_mutation_idempotency.sql',
      [
        '-- CREATE TABLE people_mutation_idempotency_record (tenant_record_id uuid);',
        '/* outer comment',
        '   /* nested comment */',
        '   CREATE TABLE people_mutation_idempotency_record (tenant_record_id uuid);',
        '*/',
        "SELECT 'CREATE TABLE people_mutation_idempotency_record (tenant_record_id uuid);';",
        "SELECT E'CREATE TABLE people_mutation_idempotency_record (tenant_record_id uuid);';",
        'SELECT $$CREATE TABLE people_mutation_idempotency_record (tenant_record_id uuid);$$;',
        'SELECT $payload$CREATE TABLE people_mutation_idempotency_record (tenant_record_id uuid);$payload$;'
      ].join('\n')
    );
    writeMigrationBackedTables(root);
    assert.deepEqual(validateMigrationBackedDatabaseObjectNames(root), [
      'Migration-backed database object is missing from migrations: people_mutation_idempotency_record'
    ]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
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

test('unfinished marker detection rejects explicit markers but allows ordinary prose', () => {
  for (const explicitMarker of [
    '# TODO\n',
    'TODO: implement this\n',
    '- [TBD]\n',
    '{{FIXME}}\n',
    '<TODO>\n'
  ]) {
    assert.equal(hasUnfinishedMarker(explicitMarker), true, explicitMarker);
  }
  for (const ordinaryProse of [
    'The placeholder text was replaced before review.\n',
    'A todo application can be imported as evidence.\n',
    'The term TBD appears inside a sentence explaining historical behavior.\n'
  ]) {
    assert.equal(hasUnfinishedMarker(ordinaryProse), false, ordinaryProse);
  }
});

test('unfinished marker detection reports the exact one-based line', () => {
  assert.deepEqual(findUnfinishedMarker('# Valid\n\nTODO: implement this\n'), {
    line: 3,
    marker: 'TODO: implement this'
  });
  assert.equal(findUnfinishedMarker('The placeholder wording is explanatory.\n'), null);
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

test('ADR index keeps provenance outside canonical status cells', () => {
  const indexText = readFileSync(new URL('../docs/adr/README.md', import.meta.url), 'utf8');
  assert.doesNotMatch(
    indexText,
    /\|\s*(?:Proposed|Accepted|Superseded|Rejected)\s+on\s+[^|]+\|/,
    'ADR status cells must remain canonical; branch provenance belongs in a separate column'
  );
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
    assert.equal(errors.length, REQUIRED_FILES.length + MIGRATION_BACKED_DATABASE_OBJECT_NAMES.length);
    assert.match(errors[0], /Missing required foundation artifact/);
    assert.ok(errors.some((error) => /Migration-backed database object is missing/.test(error)));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('foundation validator reports explicit work markers with path and line plus other failures', () => {
  const root = temporaryDirectory();
  try {
    makeMinimalValidFoundation(root);
    write(root, 'README.md', '# Valid\n\nTODO: finish this\n\n```text\n[missing](not-here.md)\n');
    write(
      root,
      'docs/TRACEABILITY.md',
      '# Trace\n\n## 2. Product traceability matrix\n\n| A | invalid_value |\n\n## 4. CWL integration traceability\n\n| B | invalid_value |\n'
    );
    const errors = validateFoundation(root);
    assert.ok(errors.some((error) => /README\.md:3: unresolved work marker TODO: finish this/.test(error)));
    assert.ok(errors.some((error) => /code fence/.test(error)));
    assert.ok(errors.some((error) => /local link target/.test(error)));
    assert.equal(errors.filter((error) => /invalid maturity value/.test(error)).length, 2);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('foundation validator accepts ordinary prose containing placeholder vocabulary', () => {
  const root = temporaryDirectory();
  try {
    makeMinimalValidFoundation(root);
    write(
      root,
      'README.md',
      '# Valid\n\nThe placeholder wording was intentionally replaced before this review.\n'
    );
    assert.deepEqual(validateFoundation(root), []);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('current traceability bounds maturity to source evidence without attesting protection', () => {
  const traceability = readFileSync(new URL('../docs/TRACEABILITY.md', import.meta.url), 'utf8');
  for (const section of ['2. Product traceability matrix', '4. CWL integration traceability']) {
    const cells = extractMaturityCells(extractSection(traceability, section));
    assert.ok(cells.length > 0, `${section}: the actual matrix must be inspected`);
    assert.equal(cells.some((cell) => cell.startsWith('implemented_on_protected_')), false,
      'a current protected classification requires evidence not captured in this source assessment');
  }
  assert.match(traceability, /develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f/);
  assert.match(traceability, /not a claim that implementation is new or absent from the default-branch base/);
  const keyverseRow = traceability.split('\n').filter((line) => line.startsWith('| Keyverse identity and authorization |'));
  assert.equal(keyverseRow.length, 1);
  assert.equal(keyverseRow[0].split('|').at(-2).trim(), 'accepted_architecture');
  assert.match(keyverseRow[0], /issuer integration remains unverified here/);
});

test('foundation validator rejects obsolete protected-main maturity in otherwise-valid matrices', () => {
  const root = temporaryDirectory();
  try {
    makeMinimalValidFoundation(root);
    const original = readFileSync(join(root, 'docs/TRACEABILITY.md'), 'utf8');
    const currentValues = [
      'implemented_on_protected_develop',
      'implemented_on_active_pr',
      'accepted_architecture',
      'planned',
      'research_only',
      'superseded',
      'out_of_scope'
    ];
    for (const originalValue of ['accepted_architecture', 'planned']) {
      for (const currentValue of currentValues) {
        write(root, 'docs/TRACEABILITY.md', original.replace(
          `| ${originalValue} |`, `| ${currentValue} |`
        ));
        assert.deepEqual(validateFoundation(root), [], `${originalValue}: ${currentValue}`);
      }
      const legacy = original.replace(
        `| ${originalValue} |`, '| implemented_on_protected_main |'
      );
      const sectionName = originalValue === 'accepted_architecture'
        ? '2. Product traceability matrix' : '4. CWL integration traceability';
      assert.deepEqual(extractMaturityCells(extractSection(legacy, sectionName)), [
        'implemented_on_protected_main'
      ], 'the legacy row must reach the canonical maturity consumer');
      write(root, 'docs/TRACEABILITY.md', legacy);
      assert.deepEqual(validateFoundation(root), [
        'docs/TRACEABILITY.md: invalid maturity value: implemented_on_protected_main'
      ], `${sectionName}: obsolete maturity must be the only rejection`);
      write(root, 'docs/TRACEABILITY.md', original);
      assert.deepEqual(validateFoundation(root), [], 'restoring the valid row must restore admission');
    }
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
