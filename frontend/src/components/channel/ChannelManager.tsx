import { useState, useEffect } from 'react'
import { useSubscriptions, usePinnedChannels, usePinChannel, useUnpinChannel } from '@/hooks/useChannels'
import LoadingSpinner from '@/components/common/LoadingSpinner'

interface ChannelManagerProps {
  isOpen: boolean
  onClose: () => void
}

export default function ChannelManager({ isOpen, onClose }: ChannelManagerProps) {
  const [search, setSearch] = useState('')
  const { data: subscriptions, isLoading: loadingSubs } = useSubscriptions()
  const { data: pinned, isLoading: loadingPinned } = usePinnedChannels()
  const pinMutation = usePinChannel()
  const unpinMutation = useUnpinChannel()

  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const pinnedIds = new Set(pinned?.map(ch => ch.channel_id) || [])
  const isLoading = loadingSubs || loadingPinned

  const filtered = subscriptions?.filter(sub =>
    sub.title.toLowerCase().includes(search.toLowerCase())
  ) || []

  const handleToggle = (channelId: string, title: string, thumbnail: string | null) => {
    if (pinnedIds.has(channelId)) {
      unpinMutation.mutate(channelId)
    } else {
      pinMutation.mutate({ channelId, title, thumbnail: thumbnail || undefined })
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="管理訂閱"
        className="glass-modal max-h-[80vh] w-full max-w-lg rounded-xl border border-slate-700/50"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-700/50 px-5 py-4">
          <h2 className="text-lg font-semibold text-white">管理訂閱</h2>
          <button
            onClick={onClose}
            className="rounded-full p-1 text-slate-400 transition hover:bg-slate-800 hover:text-slate-200"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Search */}
        <div className="border-b border-slate-700/50 px-5 py-3">
          <label htmlFor="channel-search" className="sr-only">搜尋頻道</label>
          <input
            id="channel-search"
            type="text"
            placeholder="搜尋頻道..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="glass-input w-full rounded-lg border border-slate-700 px-3 py-2 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20"
          />
        </div>

        {/* List */}
        <div className="max-h-[60vh] overflow-y-auto p-2">
          {isLoading ? (
            <LoadingSpinner className="py-12" />
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-sm text-slate-500">
                {search ? `找不到「${search}」相關的頻道` : '尚無訂閱頻道'}
              </p>
            </div>
          ) : (
            <ul className="space-y-0.5">
              {filtered.map(sub => {
                const isPinned = pinnedIds.has(sub.id)
                return (
                  <li
                    key={sub.id}
                    className="flex items-center justify-between rounded-lg px-3 py-2 transition hover:bg-slate-800/50"
                  >
                    <div className="flex items-center gap-3">
                      {sub.thumbnail ? (
                        <img src={sub.thumbnail} alt="" className="h-8 w-8 rounded-full" />
                      ) : (
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-700 text-xs font-medium text-slate-400">
                          {sub.title.charAt(0)}
                        </div>
                      )}
                      <span className="text-sm text-slate-200">{sub.title}</span>
                    </div>
                    <button
                      onClick={() => handleToggle(sub.id, sub.title, sub.thumbnail)}
                      className={`rounded-lg px-3 py-1 text-xs font-medium transition ${
                        isPinned
                          ? 'bg-blue-600/20 text-blue-400 hover:bg-blue-600/30'
                          : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                      }`}
                    >
                      {isPinned ? '取消釘選' : '釘選'}
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
