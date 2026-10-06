import { defineConfig, devices } from '@playwright/test'

// Two servers, because the two suites need different builds:
// - demo: the production build with VITE_DEMO_MODE=true, i.e. what Vercel serves
// - login: the dev server, the only place StrictMode runs effects twice
//   (that double run once sent a signed-in user back to /login; see CallbackPage.tsx)
const DEMO_PORT = 4173
const DEV_PORT = 5174 // not 5173, so a running `pnpm dev` does not block the tests

export default defineConfig({
  testDir: 'e2e',
  forbidOnly: !!process.env.CI,
  // A failure is a bug to fix, not a flake to retry
  retries: 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    ...devices['Desktop Chrome'],
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'demo', testMatch: 'demo.spec.ts', use: { baseURL: `http://localhost:${DEMO_PORT}` } },
    { name: 'login', testMatch: 'callback.spec.ts', use: { baseURL: `http://localhost:${DEV_PORT}` } },
  ],
  webServer: [
    {
      command: `pnpm exec vite build --outDir e2e-dist && pnpm exec vite preview --outDir e2e-dist --port ${DEMO_PORT} --strictPort`,
      url: `http://localhost:${DEMO_PORT}`,
      env: { VITE_DEMO_MODE: 'true' },
      timeout: 120_000,
    },
    {
      command: `pnpm exec vite --port ${DEV_PORT}`,
      url: `http://localhost:${DEV_PORT}`,
      // Set here so a local frontend/.env cannot change them; the tests answer every API call
      env: { VITE_DEMO_MODE: 'false', VITE_API_URL: 'http://localhost:8000' },
    },
  ],
})
