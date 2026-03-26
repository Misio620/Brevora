import { useState, useEffect } from 'react'
import { api } from '@/lib/api'

export default function LoginPage() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { document.title = 'Brevora — 登入' }, [])

  const handleLogin = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.get<{ auth_url: string }>('/auth/google/login')
      window.location.href = data.auth_url
    } catch {
      setLoading(false)
      setError('無法連線至伺服器，請稍後再試')
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4">
      {/* Wordmark */}
      <h1
        className="wordmark-shimmer mb-6"
        style={{
          fontFamily: "'Instrument Serif', serif",
          fontStyle: 'italic',
          fontWeight: 'bold',
          fontSize: 'clamp(4rem, 10vw, 7rem)',
          lineHeight: 1,
          letterSpacing: '-0.02em',
        }}
      >
        Brevora
      </h1>

      {/* Subtitle */}
      <div className="mb-16 flex items-center gap-3">
        <span className="block h-px w-7" style={{ background: 'rgba(148, 163, 184, 0.3)' }} />
        <span className="text-sm tracking-[0.2em] text-slate-500">
          brief • time • clarity
        </span>
        <span className="block h-px w-7" style={{ background: 'rgba(148, 163, 184, 0.3)' }} />
      </div>

      {/* Login */}
      <p className="mb-5 text-sm text-slate-400">影片太多看不完？AI 幫你抓重點</p>
      {error && (
        <p role="alert" className="mb-4 rounded-lg bg-red-500/10 px-4 py-2 text-sm text-red-400">
          {error}
        </p>
      )}
      <button
        onClick={handleLogin}
        disabled={loading}
        className="flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-8 py-3 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50"
      >
        <svg width="18" height="18" viewBox="0 0 24 24">
          <path
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
            fill="#4285F4"
          />
          <path
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            fill="#34A853"
          />
          <path
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            fill="#FBBC05"
          />
          <path
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            fill="#EA4335"
          />
        </svg>
        {loading ? '登入中...' : '使用 Google 登入'}
      </button>
    </div>
  )
}
