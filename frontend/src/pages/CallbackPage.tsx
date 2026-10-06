import { useEffect, useRef } from 'react'
import { handleCallback } from '@/lib/auth'
import LoadingSpinner from '@/components/common/LoadingSpinner'

export default function CallbackPage() {
  const handled = useRef(false)

  useEffect(() => {
    // StrictMode runs effects twice in development. handleCallback() wipes the code from
    // the URL and the code works once, so a second run would send a signed-in user to /login
    if (handled.current) return
    handled.current = true
    void handleCallback().then(result => {
      // replace() keeps /callback out of history, so Back never returns to it
      const target = { 'signed-in': '/', 'no-code': '/login', expired: '/login?error=expired' }[result]
      window.location.replace(target)
    })
  }, [])

  return (
    <div className="flex min-h-screen items-center justify-center">
      <LoadingSpinner />
      <p className="ml-3 text-slate-400">登入中...</p>
    </div>
  )
}
