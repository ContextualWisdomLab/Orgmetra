import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

/** Return the real API read document from the retained kernel and service fixture. */
export function jobAnalysisApiFixture() {
  const result = spawnSync('python3', ['-B', '-c', `
import json
import runpy
import sys
from pathlib import Path

root = Path.cwd()
sys.path[:0] = [str(root / path) for path in (
    'packages/hris-kernel/src',
    'packages/keyverse-adapter/src',
    'services/job-analysis-api/src',
)]
fixture = runpy.run_path(str(root / 'services/job-analysis-api/tests/fixtures.py'))
snapshot = fixture['clinical_psychologist_snapshot']()

class FixtureReadPort:
    def read_snapshot(self, *, tenant_record_id, analysis_record_id):
        assert tenant_record_id == snapshot.tenant_record_id
        assert analysis_record_id == snapshot.analysis_record_id
        return snapshot

from orgmetra_job_analysis_api import read_job_analysis_snapshot
view = read_job_analysis_snapshot(
    principal=fixture['read_principal'](),
    tenant_record_id=snapshot.tenant_record_id,
    analysis_record_id=snapshot.analysis_record_id,
    purpose_code='job_analysis_read',
    policy=fixture['read_policy'](),
    read_port=FixtureReadPort(),
)
assert view.snapshot == snapshot.to_snapshot()
print(json.dumps(view.snapshot, ensure_ascii=False))
`], {
    cwd: fileURLToPath(new URL('../', import.meta.url)),
    encoding: 'utf8',
    timeout: 15_000,
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
  });
  assert.equal(result.error, undefined, 'the authoritative fixture must execute');
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}
