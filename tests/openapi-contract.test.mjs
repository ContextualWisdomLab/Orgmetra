import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { validateOpenApiContract } from '../scripts/foundation-contract-core.mjs';

const canonical = readFileSync(new URL('../schemas/openapi.yaml', import.meta.url), 'utf8');

function removeOccurrence(text, fragment, occurrence = 1) {
  assert.ok(Number.isInteger(occurrence) && occurrence > 0, 'occurrence must be a positive integer');
  let searchIndex = -1;
  for (let found = 0; found < occurrence; found += 1) {
    searchIndex = text.indexOf(fragment, searchIndex + 1);
    assert.ok(searchIndex >= 0, `fixture fragment missing at occurrence ${occurrence}: ${fragment}`);
  }
  return text.slice(0, searchIndex) + text.slice(searchIndex + fragment.length);
}

test('canonical OpenAPI passes structural operation validation', () => {
  assert.deepEqual(validateOpenApiContract(canonical), []);
});

for (const testCase of [
  {
    name: 'createPersonRecord path',
    fragment: '  /person-records:\n',
    expected: /createPersonRecord.*path block/
  },
  {
    name: 'createPersonRecord scope',
    fragment: '            - orgmetra.people.write\n',
    expected: /createPersonRecord.*scope/
  },
  {
    name: 'createJobProfile scope',
    fragment: '            - orgmetra.job_architecture.write\n',
    expected: /createJobProfile.*scope/
  },
  {
    name: 'recordSelectionDecision scope',
    fragment: '            - orgmetra.talent_acquisition.write\n',
    expected: /recordSelectionDecision.*scope/
  },
  {
    name: 'first operation idempotency header',
    fragment: "        - $ref: '#/components/parameters/IdempotencyKey'\n",
    expected: /createPersonRecord.*IdempotencyKey/
  },
  {
    name: 'job profile request body binding',
    fragment: "              $ref: '#/components/schemas/CreateJobProfileCommand'\n",
    expected: /createJobProfile.*request body/
  },
  {
    name: 'job profile evidence requirement',
    fragment: '        - evidence_references\n',
    expected: /CreateJobProfileCommand.*evidence_references/
  },
  {
    name: 'selection decision evidence requirement',
    fragment: '        - evidence_references\n',
    occurrence: 2,
    expected: /RecordSelectionDecisionCommand.*evidence_references/
  },
  {
    name: 'job profile evidence maxItems',
    fragment: '          maxItems: 100\n',
    expected: /CreateJobProfileCommand.*maxItems/
  },
  {
    name: 'selection decision evidence maxItems',
    fragment: '          maxItems: 100\n',
    occurrence: 2,
    expected: /RecordSelectionDecisionCommand.*maxItems/
  },
  {
    name: 'job profile evidence uniqueness',
    fragment: '          uniqueItems: true\n',
    expected: /CreateJobProfileCommand.*unique/
  },
  {
    name: 'selection decision evidence uniqueness',
    fragment: '          uniqueItems: true\n',
    occurrence: 2,
    expected: /RecordSelectionDecisionCommand.*unique/
  },
  {
    name: 'person 201 response',
    fragment: "        '201':\n",
    expected: /createPersonRecord.*response.*201/
  },
  {
    name: 'job 400 response',
    fragment: "        '400':\n",
    occurrence: 2,
    expected: /createJobProfile.*response.*400/
  },
  {
    name: 'selection 401 response',
    fragment: "        '401':\n",
    occurrence: 3,
    expected: /recordSelectionDecision.*response.*401/
  },
  {
    name: 'selection 403 response',
    fragment: "        '403':\n",
    occurrence: 3,
    expected: /recordSelectionDecision.*response.*403/
  },
  {
    name: 'selection 409 response',
    fragment: "        '409':\n",
    occurrence: 3,
    expected: /recordSelectionDecision.*response.*409/
  },
  {
    name: 'selection 422 response',
    fragment: "        '422':\n",
    expected: /recordSelectionDecision.*response.*422/
  },
  {
    name: 'safe support reference error field',
    fragment: '        - support_reference\n',
    expected: /ErrorResponse.*support_reference/
  },
  {
    name: 'createEmploymentRecord path',
    fragment: '  /employment-records:\n',
    expected: /createEmploymentRecord.*path block/
  },
  {
    name: 'createEmploymentRecord scope',
    fragment: '            - orgmetra.people.write\n',
    occurrence: 2,
    expected: /createEmploymentRecord.*scope/
  },
  {
    name: 'createPositionRecord path',
    fragment: '  /position-records:\n',
    expected: /createPositionRecord.*path block/
  },
  {
    name: 'createPositionRecord scope',
    fragment: '            - orgmetra.job_architecture.write\n',
    occurrence: 2,
    expected: /createPositionRecord.*scope/
  },
  {
    name: 'createAssignmentRecord path',
    fragment: '  /assignment-records:\n',
    expected: /createAssignmentRecord.*path block/
  },
  {
    name: 'createAssignmentRecord scope',
    fragment: '            - orgmetra.people.write\n',
    occurrence: 3,
    expected: /createAssignmentRecord.*scope/
  },
  {
    name: 'employment evidence requirement',
    fragment: '        - evidence_references\n',
    occurrence: 3,
    expected: /CreateEmploymentRecordCommand.*evidence_references/
  },
  {
    name: 'assignment confirmation requirement',
    fragment: '        - confirmation_reference\n',
    occurrence: 5,
    expected: /CreateAssignmentRecordCommand.*confirmation/
  }
]) {
  test(`structural OpenAPI gate rejects missing ${testCase.name}`, () => {
    const mutated = removeOccurrence(canonical, testCase.fragment, testCase.occurrence ?? 1);
    const errors = validateOpenApiContract(mutated);
    assert.ok(errors.some((error) => testCase.expected.test(error)), errors.join('\n'));
  });
}

test('structural OpenAPI gate rejects a version downgrade', () => {
  const mutated = canonical.replace('openapi: 3.2.0\n', 'openapi: 3.1.0\n');
  const errors = validateOpenApiContract(mutated);
  assert.ok(errors.some((error) => /expected version 3\.2\.0/.test(error)), errors.join('\n'));
});

test('structural OpenAPI gate rejects internal trace identifiers anywhere in the document', () => {
  const errors = validateOpenApiContract(`${canonical}\ntrace_id:\n  type: string\n`);
  assert.ok(
    errors.some((error) => /OpenAPI document.*trace identifiers/.test(error)),
    errors.join('\n')
  );
});

test('structural OpenAPI gate rejects an empty-scope OIDC requirement', () => {
  const errors = validateOpenApiContract(`${canonical}\nkeyverse_oidc: []\n`);
  assert.ok(errors.some((error) => /empty-scope OIDC/.test(error)), errors.join('\n'));
});

test('buyer-facing changelog and README preserve protected People mutation truth', () => {
  const readme = readFileSync(new URL('../README.md', import.meta.url), 'utf8');
  const changelog = readFileSync(new URL('../CHANGELOG.md', import.meta.url), 'utf8');
  const mutationLine = changelog
    .split('\n')
    .find((line) => line.includes('`POST /v1/employment-records`'));

  assert.ok(mutationLine, 'People mutation runtime changelog entry is missing');
  assert.doesNotMatch(
    readme,
    /GET-only People API/i,
    'README must not demote the integrated People API to GET-only'
  );
  assert.match(
    readme,
    /purpose-bound People mutation/i,
    'README must describe the protected People mutation boundary'
  );
  assert.match(
    mutationLine,
    /Protected governed People mutation/i,
    'integrated People mutations must be recorded as protected runtime'
  );
  assert.doesNotMatch(
    mutationLine,
    /contract-only|non-shipped runtime/i,
    'protected People mutations must not be mislabeled as non-shipped'
  );
});
