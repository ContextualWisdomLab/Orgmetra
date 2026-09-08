import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const REQUIRED_MODEL_BOUNDARY_DOCS = Object.freeze([
  'AGENTS.md',
  'CLAUDE.md',
  'docs/TRD.md',
  'docs/SECURITY.md',
  'docs/traceability/contextual-orchestrator-routing.md'
]);

function read(path) {
  return readFileSync(path, 'utf8');
}

test('model-backed guidance routes through the released contextual-orchestrator contract', () => {
  for (const path of REQUIRED_MODEL_BOUNDARY_DOCS) {
    const content = read(path);
    assert.match(content, /contextual[- ]orchestrator/i, `${path} must name the contextual-orchestrator owner boundary`);
    assert.match(content, /orchestrator\/free/, `${path} must require the free orchestrator route`);
    assert.match(content, /gateway token/i, `${path} must bind model-backed automation to gateway authentication`);
  }
});

test('Orgmetra does not prescribe direct provider credentials or routing', () => {
  const agents = read('AGENTS.md');
  assert.doesNotMatch(
    agents,
    /NVIDIA_NIM_API_KEY|NVIDIA_NIM_SUB_API_KEY|OPENROUTER_API_KEY|OPENAI_API_KEY|BYTEZ_API_KEY/,
    'AGENTS.md must not make a provider credential part of the Orgmetra consumer contract'
  );
  assert.match(agents, /provider\/model\/group/i);
  assert.match(agents, /fail closed/i);
});
