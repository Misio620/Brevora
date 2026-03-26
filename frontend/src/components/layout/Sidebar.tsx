import { usePinnedChannels } from '@/hooks/useChannels'

interface Filters {
  status: string
  favorites: boolean
  channel: string
  search: string
}

interface SidebarProps {
  filters: Filters
  onFilterChange: (filters: Filters) => void
  onOpenManager: () => void
  mobile?: boolean
}

export default function Sidebar({ filters, onFilterChange, onOpenManager, mobile }: SidebarProps) {
  const { data: pinnedChannels } = usePinnedChannels()

  const update = (key: keyof Filters, value: string | boolean) => {
    onFilterChange({ ...filters, [key]: value })
  }

  const clearFilters = () => {
    onFilterChange({ status: 'all', favorites: false, channel: 'all', search: '' })
  }

  const content = (
    <>
      {!mobile && (
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">篩選</h3>
          <button
            onClick={clearFilters}
            className="text-xs text-slate-400 transition hover:text-slate-200"
          >
            清除
          </button>
        </div>
      )}

      {/* Search */}
      <div className="mb-4">
        <label htmlFor={mobile ? 'mobile-search' : 'sidebar-search'} className="sr-only">搜尋影片</label>
        <input
          id={mobile ? 'mobile-search' : 'sidebar-search'}
          type="text"
          placeholder="搜尋影片..."
          value={filters.search}
          onChange={e => update('search', e.target.value)}
          className="glass-input w-full rounded-lg border border-slate-700 px-3 py-2 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20"
        />
      </div>

      {/* Status */}
      <div className="mb-4">
        <label className="mb-1.5 block text-xs font-medium text-slate-400">處理狀態</label>
        <div className="flex flex-col gap-1">
          {[
            { value: 'all', label: '全部' },
            { value: 'done', label: '已完成' },
            { value: 'pending', label: '未完成' },
          ].map(opt => (
            <label key={opt.value} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-slate-800/50">
              <input
                type="radio"
                name={mobile ? 'mobile-status' : 'status'}
                value={opt.value}
                checked={filters.status === opt.value}
                onChange={() => update('status', opt.value)}
                className="accent-blue-500"
              />
              <span className="text-slate-200">{opt.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Favorites */}
      <div className="mb-4">
        <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-slate-800/50">
          <input
            type="checkbox"
            checked={filters.favorites}
            onChange={e => update('favorites', e.target.checked)}
            className="accent-blue-500"
          />
          <span className="text-slate-200">僅顯示收藏</span>
        </label>
      </div>

      {/* Channel */}
      <div className="mb-4">
        <label className="mb-1.5 block text-xs font-medium text-slate-400">頻道</label>
        <select
          value={filters.channel}
          onChange={e => update('channel', e.target.value)}
          className="glass-input w-full rounded-lg border border-slate-700 px-2 py-2 text-sm text-slate-200 outline-none transition focus:border-blue-500/50"
        >
          <option value="all">全部頻道</option>
          {pinnedChannels?.map(ch => (
            <option key={ch.channel_id} value={ch.channel_id}>
              {ch.title}
            </option>
          ))}
        </select>
      </div>

      {/* Manage button */}
      <button
        onClick={onOpenManager}
        className="w-full rounded-lg border border-slate-700 py-2 text-sm font-medium text-slate-400 transition hover:bg-slate-800"
      >
        管理訂閱
      </button>

      {mobile && (
        <button
          onClick={clearFilters}
          className="mt-3 w-full rounded-lg py-2 text-sm text-slate-500 transition hover:text-slate-300"
        >
          清除所有篩選
        </button>
      )}
    </>
  )

  if (mobile) return content

  return (
    <aside className="glass-sidebar hidden w-56 shrink-0 border-r border-slate-700/50 p-4 md:block">
      {content}
    </aside>
  )
}
