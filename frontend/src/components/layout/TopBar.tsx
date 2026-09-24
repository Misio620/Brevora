import { useAuth } from '@/hooks/useAuth'
import { useSyncVideos } from '@/hooks/useVideos'
import { useToast } from '@/components/common/Toast'
import { logout } from '@/lib/auth'

export default function TopBar() {
  const { user } = useAuth()
  const syncMutation = useSyncVideos()
  const { toast } = useToast()

  const handleLogout = () => {
    if (window.confirm('確定要登出嗎？')) {
      logout()
    }
  }

  const handleSync = () => {
    syncMutation.mutate(undefined, {
      onSuccess: ({ new_videos, failed_channels }) => {
        const summary = new_videos > 0 ? `同步完成，新增 ${new_videos} 部影片` : '已是最新，沒有新影片'
        if (failed_channels > 0) {
          toast(`${summary}（${failed_channels} 個頻道同步失敗）`, 'info')
        } else {
          toast(summary, 'success')
        }
      },
      onError: (err) => {
        toast(`同步失敗：${err.message}`, 'error')
      },
    })
  }

  return (
    <header className="glass-nav flex h-14 items-center justify-between border-b border-slate-700/50 px-4">
      <h1
        className="text-lg text-white"
        style={{ fontFamily: "'Instrument Serif', serif", fontStyle: 'italic' }}
      >
        Brevora
      </h1>

      <div className="flex items-center gap-3">
        <button
          onClick={handleSync}
          disabled={syncMutation.isPending}
          aria-label={syncMutation.isPending ? '同步中' : '同步影片'}
          className="flex items-center gap-1.5 rounded-lg bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-300 transition hover:bg-slate-700 disabled:opacity-50"
        >
          <svg
            className={`h-4 w-4 ${syncMutation.isPending ? 'animate-spin' : ''}`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="23 4 23 10 17 10" />
            <polyline points="1 20 1 14 7 14" />
            <path d="M3.51 9a9 9 0 0114.13-3.36L23 10M1 14l5.36 4.36A9 9 0 0020.49 15" />
          </svg>
          {syncMutation.isPending ? '同步中...' : '同步'}
        </button>

        <div className="flex items-center gap-2">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt={`${user.display_name || '使用者'}的頭像`} className="h-7 w-7 rounded-full" />
          ) : (
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-700 text-xs font-medium text-slate-300">
              {user?.display_name?.charAt(0) || '?'}
            </div>
          )}
          <button
            onClick={handleLogout}
            aria-label="登出帳號"
            className="rounded px-2 py-1 text-xs text-slate-400 transition hover:bg-slate-800 hover:text-slate-200"
          >
            登出
          </button>
        </div>
      </div>
    </header>
  )
}
