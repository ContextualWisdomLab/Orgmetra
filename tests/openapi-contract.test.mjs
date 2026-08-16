import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { validateOpenApiContract } from '../scripts/foundation-contract-core.mjs';

const canonical = readFileSync(new URL('../schemas/openapi.yaml', import.meta.url), 'utf8');

function removeOnce(text, fragment) {
  assert.ok(text.includes(fragment), `fixture fragment missing: ${fragment}`);
  return text.replace(fragment, '');
}

test('canonical OpenAPI passes structural operation validation', () => {
  assert.deepEqual(validateOpenApiContract(canonical), []);
});

for (const testCase of [
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
    name: 'safe support reference error field',
    fragment: '        - support_reference\n',
    expected: /ErrorResponse.*support_reference/
  }
]) {
  test(`structural OpenAPI gate rejects missing ${testCase.name}`, () => {
    let mutated = canonical;
    const count = testCase.occurrence ?? 1;
    for (let index = 0; index < count; index += 1) {
      mutated = removeOnce(mutated, testCase.fragment);
    }
    const errors = validateOpenApiContract(mutated);
    assert.ok(errors.some((error) => testCase.expected.test(error)), errors.join('\n'));
  });
}
