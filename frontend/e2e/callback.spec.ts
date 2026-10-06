// Runs against the dev server, where StrictMode runs effects twice: the one-time login code
// must still be exchanged exactly once (see CallbackPage.tsx). The backend is faked here
import { test, expect, type Page } from '@playwright/test'

const API = 'http://localhost:8000'
const CORS = {
  'access-control-allow-origin': '*',
  'access-control-allow-headers': 'Content-Type, Authorization',
  'access-control-allow-methods': 'GET, POST, PATCH, DELETE',
}

// Answers the API like a backend that accepts only `validCode`, once
async function fakeBackend(page: Page, validCode: string) {
  const exchanged: string[] = []
  let used = false

  await page.route(`${API}/**`, async route => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    const json = (status: number, body: unknown) => route.fulfill({ status, headers: CORS, json: body })

    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers: CORS })
    if (path === '/auth/exchange') {
      const { code } = request.postDataJSON()
      exchanged.push(code)
      // A real backend takes a moment. Answering instantly hides the StrictMode bug: the
      // second run's redirect to /login would be overtaken by the first run's redirect to /
      await new Promise(resolve => setTimeout(resolve, 500))
      if (code !== validCode || used) return json(400, { detail: 'Invalid or expired login code' })
      used = true
      return json(200, { access_token: 'test-jwt', token_type: 'bearer' })
    }
    if (request.headers()['authorization'] !== 'Bearer test-jwt') return json(401, { detail: 'Not authenticated' })
    if (path === '/auth/me') return json(200, { id: 'u1', email: 'tester@example.com', display_name: 'Tester', avatar_url: null })
    if (path === '/videos/feed') return json(200, { videos: [], total: 0, page: 1, per_page: 20, has_more: false })
    if (path.startsWith('/channels/')) return json(200, [])
    return json(404, { detail: 'Not faked in this test' })
  })

  return exchanged
}

const pathname = (page: Page) => () => new URL(page.url()).pathname

test('a valid code signs in once, even though StrictMode runs the page twice', async ({ page }) => {
  const exchanged = await fakeBackend(page, 'good-code')

  await page.goto('/callback#code=good-code')

  await expect.poll(pathname(page)).toBe('/')
  expect(exchanged).toEqual(['good-code'])
  expect(await page.evaluate(() => localStorage.getItem('token'))).toBe('test-jwt')
  expect(page.url()).not.toContain('good-code')
})

test('a used or expired code goes back to login with an explanation', async ({ page }) => {
  const exchanged = await fakeBackend(page, 'good-code')

  await page.goto('/callback#code=stale-code')

  await expect.poll(pathname(page)).toBe('/login')
  await expect(page.getByRole('alert')).toHaveText('登入連結已失效，請重新登入')
  expect(exchanged).toEqual(['stale-code'])
  expect(await page.evaluate(() => localStorage.getItem('token'))).toBeNull()
})

test('opening the callback page without a code goes to login', async ({ page }) => {
  const exchanged = await fakeBackend(page, 'good-code')

  await page.goto('/callback')

  await expect.poll(pathname(page)).toBe('/login')
  await expect(page.getByRole('alert')).toHaveCount(0)
  expect(exchanged).toEqual([])
})
