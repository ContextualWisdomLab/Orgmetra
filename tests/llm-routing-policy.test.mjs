import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

function repositoryText(relativePath) {
  return readFileSync(new URL(`../${relativePath}`, import.meta.url), 'utf8');
}

test('consumer guidance routes model-backed Actions only through contextual-orchestrator free', () => {
  const agents = repositoryText('AGENTS.md');

  assert.match(agents, /`orchestrator\/free`/);
  assert.match(agents, /contextual-orchestrator/);
  assert.match(agents, /gateway token/i);
  assert.doesNotMatch(agents, /NVIDIA_NIM_API_KEY/);
  assert.doesNotMatch(agents, /OPENAI_API_KEY/);
  assert.doesNotMatch(agents, /OPENROUTER_API_KEY/);
  assert.doesNotMatch(agents, /BYTEZ_API_KEY/);
});

test('core-boundary guidance separates ontology release from catalog governance', () => {
  const claude = repositoryText('CLAUDE.md');

  assert.match(claude, /ConceptWeave owns ontology/);
  assert.match(claude, /semantic-data-portal owns catalog/);
  assert.match(claude, /contextual-orchestrator owns bounded LLM orchestration traces/);
  assert.doesNotMatch(claude, /Semantic Data Portal owns occupation\/skill\/ability ontology/);
});
