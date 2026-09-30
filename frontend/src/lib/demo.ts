// Demo mode: answers the API from pre-generated data so the app works without login or a backend.
// Notes in demo-data.json are real Gemini output from scripts/generate_demo_data.py.
// Per-visitor state (read, favorite, pinned channels) lives in this browser's localStorage.
import demoData from '@/demo/demo-data.json'
import { DEMO_STORAGE_KEY } from './demoMode'

interface DemoVideo {
  youtube_id: string
  channel_id: string
  channel_title: string
  title: string
  translated_title: string | null
  thumbnail: string | null
  published_at: string
  summary?: string | null
}

interface VideoState {
  is_read: boolean
  is_favorite: boolean
  note: string
}

interface DemoState {
  videos: Record<string, VideoState>
  pinned: string[]
}

const DEFAULT_STATE: VideoState = { is_read: false, is_favorite: false, note: '' }
const videos = demoData.videos as DemoVideo[]
const channels = demoData.channels

function loadState(): DemoState {
  try {
    const saved = localStorage.getItem(DEMO_STORAGE_KEY)
    if (saved) return JSON.parse(saved)
  } catch {
    // Storage blocked or corrupted: start fresh
  }
  return { videos: {}, pinned: channels.map(ch => ch.id) }
}

function saveState(state: DemoState) {
  try {
    localStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(state))
  } catch {
    // Storage blocked: changes last until the page reloads
  }
}

const state = loadState()

function toResponse(video: DemoVideo) {
  return {
    youtube_id: video.youtube_id,
    channel_id: video.channel_id,
    channel_title: video.channel_title,
    title: video.title,
    translated_title: video.translated_title,
    thumbnail: video.thumbnail,
    published_at: video.published_at,
    summary: video.summary ?? null,
    processing_status: video.summary ? 'done' : 'error',
    error_message: video.summary ? null : 'Demo 模式無法即時生成筆記',
    ...DEFAULT_STATE,
    ...state.videos[video.youtube_id],
  }
}

function findVideo(youtubeId: string) {
  const video = videos.find(v => v.youtube_id === youtubeId)
  if (!video) throw new Error('Video not found')
  return video
}

// Mirrors the filtering and pagination of GET /videos/feed in backend/app/routers/videos.py
function feed(params: URLSearchParams) {
  const page = Number(params.get('page') || 1)
  const perPage = Number(params.get('per_page') || 20)
  const channelId = params.get('channel_id')
  const status = params.get('status')
  const search = params.get('search')?.toLowerCase()

  let result = videos
    .filter(v => state.pinned.includes(v.channel_id))
    .filter(v => !channelId || v.channel_id === channelId)
    .map(toResponse)

  if (status === 'done') result = result.filter(v => v.processing_status === 'done')
  else if (status === 'pending') result = result.filter(v => v.processing_status !== 'done')
  if (params.get('favorites') === 'true') result = result.filter(v => v.is_favorite)
  if (search) {
    result = result.filter(v =>
      [v.title, v.channel_title, v.translated_title, v.summary].some(text => text?.toLowerCase().includes(search)),
    )
  }

  result.sort((a, b) => b.published_at.localeCompare(a.published_at))
  const offset = (page - 1) * perPage
  return {
    videos: result.slice(offset, offset + perPage),
    total: result.length,
    page,
    per_page: perPage,
    has_more: offset + perPage < result.length,
  }
}

export async function demoRequest(method: string, path: string, body?: string): Promise<unknown> {
  const url = new URL(path, 'http://demo')
  const route = `${method} ${url.pathname}`
  const data = body ? JSON.parse(body) : {}
  let match: RegExpMatchArray | null

  if (route === 'GET /auth/me') {
    return { id: 'demo', email: 'demo@brevora.app', display_name: 'Demo 訪客', avatar_url: null }
  }
  if (route === 'GET /channels/subscriptions') return channels
  if (route === 'GET /channels/pinned') {
    return channels
      .filter(ch => state.pinned.includes(ch.id))
      .map(ch => ({ id: ch.id, channel_id: ch.id, title: ch.title, thumbnail: ch.thumbnail }))
  }
  if ((match = route.match(/^POST \/channels\/pin\/(.+)$/))) {
    if (!state.pinned.includes(match[1])) state.pinned = [...state.pinned, match[1]]
    saveState(state)
    return { status: 'pinned' }
  }
  if ((match = route.match(/^DELETE \/channels\/unpin\/(.+)$/))) {
    state.pinned = state.pinned.filter(id => id !== match![1])
    saveState(state)
    return undefined
  }
  if (route === 'GET /videos/feed') return feed(url.searchParams)
  if (route === 'POST /videos/sync') return { status: 'done', new_videos: 0, failed_channels: 0 }
  if ((match = route.match(/^PATCH \/videos\/(.+)\/metadata$/))) {
    const video = findVideo(match[1])
    const current = { ...DEFAULT_STATE, ...state.videos[video.youtube_id] }
    for (const key of ['is_read', 'is_favorite', 'note'] as const) {
      if (data[key] !== undefined && data[key] !== null) Object.assign(current, { [key]: data[key] })
    }
    state.videos = { ...state.videos, [video.youtube_id]: current }
    saveState(state)
    return toResponse(video)
  }
  if ((match = route.match(/^POST \/videos\/(.+)\/process$/))) {
    return { status: 'error', youtube_id: findVideo(match[1]).youtube_id }
  }
  if ((match = route.match(/^GET \/videos\/(.+)$/))) return toResponse(findVideo(match[1]))

  throw new Error(`Demo 模式不支援此操作（${route}）`)
}
