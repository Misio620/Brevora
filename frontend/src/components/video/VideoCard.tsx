import type { VideoWithState } from '@/hooks/useVideos'
import { useUpdateMetadata } from '@/hooks/useVideos'

interface VideoCardProps {
  video: VideoWithState
  onClick: () => void
}

const STATUS_STYLES: Record<string, { label: string; className: string }> = {
  done: { label: '完成', className: 'bg-emerald-500/20 text-emerald-400' },
  processing: { label: '處理中', className: 'bg-amber-500/20 text-amber-400' },
  error: { label: '錯誤', className: 'bg-red-500/20 text-red-400' },
  pending: { label: '待處理', className: 'bg-slate-700 text-slate-400' },
}

export default function VideoCard({ video, onClick }: VideoCardProps) {
  const updateMeta = useUpdateMetadata()

  const statusInfo = STATUS_STYLES[video.processing_status] || STATUS_STYLES.pending
  const displayTitle = video.translated_title || video.title
  const subtitle = video.translated_title ? video.title : null

  const toggleFavorite = (e: React.MouseEvent) => {
    e.stopPropagation()
    updateMeta.mutate({
      youtubeId: video.youtube_id,
      data: { is_favorite: !video.is_favorite },
    })
  }

  const openYouTube = (e: React.MouseEvent) => {
    e.stopPropagation()
    window.open(`https://www.youtube.com/watch?v=${video.youtube_id}`, '_blank')
  }

  const formatDate = (d: string | null) => {
    if (!d) return ''
    return new Date(d).toLocaleDateString('zh-TW')
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick() } }}
      className="video-card group flex cursor-pointer gap-3 rounded-xl border border-slate-700/50 p-3 transition hover:border-blue-500/30 focus-visible:outline-2 focus-visible:outline-blue-500"
    >
      {/* Thumbnail */}
      <div className="relative h-24 w-40 shrink-0 overflow-hidden rounded-lg bg-slate-700">
        {video.thumbnail ? (
          <img src={video.thumbnail} alt={displayTitle} width={160} height={96} loading="lazy" className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-slate-500">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
        )}
        <span className={`absolute left-1.5 top-1.5 rounded px-1.5 py-0.5 text-[10px] font-medium ${statusInfo.className}`}>
          {statusInfo.label}
        </span>
      </div>

      {/* Content */}
      <div className="flex min-w-0 flex-1 flex-col justify-between">
        <div>
          <h3 className="line-clamp-2 text-sm font-medium leading-tight text-white">
            {displayTitle}
          </h3>
          {subtitle && (
            <p className="mt-0.5 line-clamp-1 text-xs text-slate-500">{subtitle}</p>
          )}
          <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-400">
            <span>{video.channel_title}</span>
            <span>·</span>
            <span>{formatDate(video.published_at)}</span>
          </div>
        </div>
        {video.summary && (
          <p className="mt-1 line-clamp-2 text-xs text-slate-500">
            {video.summary.substring(0, 120)}...
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="flex shrink-0 flex-col items-center gap-1">
        <button
          onClick={toggleFavorite}
          aria-label={video.is_favorite ? '取消收藏' : '加入收藏'}
          className={`rounded-full p-2 transition hover:bg-slate-700/60 ${video.is_favorite ? 'text-amber-400' : 'text-slate-500'}`}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill={video.is_favorite ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
        </button>
        <button
          onClick={openYouTube}
          aria-label="開啟原始影片"
          className="rounded-full p-2 text-slate-500 transition hover:bg-slate-700/60 hover:text-blue-400"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
        </button>
      </div>
    </div>
  )
}
