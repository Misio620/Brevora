// The Vercel demo is what interviewers open: no login, real notes, state kept in the browser
import { test, expect } from '@playwright/test'

const TIMESTAMP_LINK = /^(\d{1,2}:)?\d{1,2}:\d{2}$/

test('opens straight to the feed without signing in', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('note')).toContainText('Demo 模式')
  await expect(page.locator('.video-card')).toHaveCount(6)
  expect(new URL(page.url()).pathname).toBe('/')
})

test('a note links every timestamp to that second of the video', async ({ page }) => {
  await page.goto('/')
  await page.locator('.video-card').first().click()

  await expect(page).toHaveURL(/\/video\/[\w-]+$/)
  const youtubeId = new URL(page.url()).pathname.split('/').pop()!
  await expect(page.getByRole('heading', { name: '節目筆記' })).toBeVisible()

  const timestamps = page.getByRole('link', { name: TIMESTAMP_LINK })
  await expect(timestamps.first()).toBeVisible()
  for (const link of await timestamps.all()) {
    await expect(link).toHaveAttribute('href', new RegExp(`^https://www\\.youtube\\.com/watch\\?v=${youtubeId}&t=\\d+s$`))
    await expect(link).toHaveAttribute('target', '_blank')
  }
})

test('my note and favorites survive a reload', async ({ page }) => {
  await page.goto('/')
  const card = page.locator('.video-card').first()
  await card.getByRole('button', { name: '加入收藏' }).click()
  await expect(card.getByRole('button', { name: '取消收藏' })).toBeVisible()

  await card.click()
  const note = page.getByRole('textbox', { name: '我的筆記' })
  await note.fill('測試筆記：下週試試這個做法')
  await expect(page.getByText('已儲存')).toBeVisible()

  await page.reload()
  await expect(note).toHaveValue('測試筆記：下週試試這個做法')

  await page.goto('/')
  await expect(card.getByRole('img', { name: '有我的筆記' })).toBeVisible()
  await expect(card.getByRole('button', { name: '取消收藏' })).toBeVisible()
})
