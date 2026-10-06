import { useEffect } from 'react'
import { handleCallback } from '@/lib/auth'
import LoadingSpinner from '@/components/common/LoadingSpinner'

export default function CallbackPage() {
  useEffect(() => {
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
