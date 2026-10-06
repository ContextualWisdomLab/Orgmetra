import { defineConfig, devices } from '@playwright/test';

// Reject malformed overrides before interpolating a shell command or starting a fixture.
const port = process.env.ORGMETRA_WORKSPACE_PORT ?? '4173';
if (!/^[1-9][0-9]{0,4}$/.test(port) || Number(port) > 65535) {
  throw new Error('ORGMETRA_WORKSPACE_PORT must be a canonical decimal TCP port from 1 to 65535');
}

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 15_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI
    ? [['line'], ['html', { outputFolder: 'playwright-report', open: 'never' }]]
    : 'list',
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: `python3 -m http.server ${port} --bind 127.0.0.1`,
    url: `http://127.0.0.1:${port}/apps/hr-workspace/index.html`,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
