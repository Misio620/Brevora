import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import TopBar from '@/components/layout/TopBar'
import Sidebar from '@/components/layout/Sidebar'
import VideoGrid from '@/components/video/VideoGrid'
import ChannelManager from '@/components/channel/ChannelManager'
import type { VideoWithState } from '@/hooks/useVideos'

export default function DashboardPage() {
  const navigate = useNavigate()
  const [filters, setFilters] = useState({
    status: 'all',
    favorites: false,
    channel: 'all',
    search: '',
  })
  const [page, setPage] = useState(1)
  const [isManagerOpen, setIsManagerOpen] = useState(false)
  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false)

  useEffect(() => { document.title = 'Brevora — 影片總覽' }, [])

  // Reset page when filters change
  const handleFilterChange = (newFilters: typeof filters) => {
    setFilters(newFilters)
    setPage(1)
  }

  const handleVideoSelect = (video: VideoWithState) => {
    navigate(`/video/${video.youtube_id}`)
  }

  const hasActiveFilters = filters.status !== 'all' || filters.favorites || filters.channel !== 'all' || filters.search !== ''

  return (
    <div className="flex h-screen flex-col bg-transparent">
      <TopBar />

      {/* Mobile filter button */}
      <div className="flex items-center border-b border-slate-700/50 px-4 py-2 md:hidden">
        <button
          onClick={() => setIsMobileFilterOpen(true)}
          aria-label="開啟篩選"
          className="flex items-center gap-1.5 rounded-lg bg-slate-800 px-3 py-2 text-sm font-medium text-slate-300 transition hover:bg-slate-700"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
          </svg>
          篩選
          {hasActiveFilters && (
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-blue-500 text-[10px] text-white">!</span>
          )}
        </button>
      </div>

      {/* Mobile filter overlay */}
      {isMobileFilterOpen && (
        <div className="fixed inset-0 z-40 md:hidden" onClick={() => setIsMobileFilterOpen(false)}>
          <div className="absolute inset-0 bg-black/50" />
          <div
            className="absolute left-0 top-0 h-full w-64 border-r border-slate-700/50 p-4"
            style={{ background: 'rgba(15, 23, 42, 0.95)' }}
            onClick={e => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200">篩選</h3>
              <button
                onClick={() => setIsMobileFilterOpen(false)}
                aria-label="關閉篩選"
                className="rounded-full p-1 text-slate-400 transition hover:bg-slate-800 hover:text-slate-200"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <Sidebar
              filters={filters}
              onFilterChange={(f) => { handleFilterChange(f); setIsMobileFilterOpen(false) }}
              onOpenManager={() => { setIsMobileFilterOpen(false); setIsManagerOpen(true) }}
              mobile
            />
          </div>
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        <Sidebar
          filters={filters}
          onFilterChange={handleFilterChange}
          onOpenManager={() => setIsManagerOpen(true)}
        />
        <main id="main-content" className="flex min-w-0 flex-1 flex-col">
          <VideoGrid
            filters={filters}
            page={page}
            onPageChange={setPage}
            onVideoSelect={handleVideoSelect}
          />
        </main>
      </div>
      <ChannelManager
        isOpen={isManagerOpen}
        onClose={() => setIsManagerOpen(false)}
      />
    </div>
  )
}
