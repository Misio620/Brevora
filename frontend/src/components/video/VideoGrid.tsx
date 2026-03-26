import { useVideoFeed, type VideoWithState } from '@/hooks/useVideos'
import VideoCard from './VideoCard'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import EmptyState from '@/components/common/EmptyState'

interface VideoGridProps {
  filters: {
    status: string
    favorites: boolean
    channel: string
    search: string
  }
  page: number
  onPageChange: (page: number) => void
  onVideoSelect: (video: VideoWithState) => void
}

export default function VideoGrid({ filters, page, onPageChange, onVideoSelect }: VideoGridProps) {
  const { data, isLoading, error } = useVideoFeed({
    page,
    per_page: 20,
    channel_id: filters.channel !== 'all' ? filters.channel : undefined,
    status: filters.status !== 'all' ? filters.status : undefined,
    favorites: filters.favorites || undefined,
    search: filters.search || undefined,
  })

  if (isLoading) {
    return <LoadingSpinner className="py-20" />
  }

  if (error) {
    return (
      <EmptyState
        title="載入失敗"
        description={error.message}
      />
    )
  }

  if (!data?.videos.length) {
    return (
      <EmptyState
        title="沒有找到影片"
        description="試試調整篩選條件，或先同步訂閱頻道的最新影片"
      />
    )
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex-1 space-y-2 overflow-y-auto p-4">
        {data.videos.map(video => (
          <VideoCard
            key={video.youtube_id}
            video={video}
            onClick={() => onVideoSelect(video)}
          />
        ))}
      </div>

      {/* Pagination */}
      {data.total > 20 && (
        <div className="flex items-center justify-between border-t border-slate-700/50 bg-transparent px-4 py-3">
          <span className="text-sm text-slate-400">
            共 {data.total} 部影片
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              aria-label="上一頁"
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800 disabled:opacity-30"
            >
              上一頁
            </button>
            <span className="flex items-center px-2 text-sm text-slate-400">
              第 {page} 頁
            </span>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={!data.has_more}
              aria-label="下一頁"
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800 disabled:opacity-30"
            >
              下一頁
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
