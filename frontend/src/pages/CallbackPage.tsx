import { useEffect, useRef } from 'react'
import { handleCallback } from '@/lib/auth'
import LoadingSpinner from '@/components/common/LoadingSpinner'

export default function CallbackPage() {
  const handled = useRef(false)

  useEffect(() => {
    // StrictMode runs effects twice in development. handleCallback() wipes the token
    // from the URL, so a second run would find none and send a signed-in user to /login
    if (handled.current) return
    handled.current = true
    const token = handleCallback()
    // replace() keeps /callback out of history, so Back never returns to it
    window.location.replace(token ? '/' : '/login')
  }, [])

  return (
    <div className="flex min-h-screen items-center justify-center">
      <LoadingSpinner />
      <p className="ml-3 text-slate-400">登入中...</p>
    </div>
  )
}
