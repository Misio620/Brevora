import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useVideo, useUpdateMetadata, useProcessVideo } from '@/hooks/useVideos'
import SummaryDisplay from '@/components/video/SummaryDisplay'
import LoadingSpinner from '@/components/common/LoadingSpinner'

export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: video, isLoading, refetch } = useVideo(id || '')
  const updateMeta = useUpdateMetadata()
  const processMutation = useProcessVideo()

  // Mark as read on mount
  useEffect(() => {
    if (id && video && !video.is_read) {
      updateMeta.mutate({ youtubeId: id, data: { is_read: true } })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only trigger on id/read state change, mutation ref is stable enough
  }, [id, video?.is_read])

  // Auto-trigger processing if no summary
  useEffect(() => {
    if (video && !video.summary && video.processing_status === 'pending') {
      processMutation.mutate(id!)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only trigger on processing status change
  }, [id, video?.processing_status, video?.summary])

  // Poll while processing
  useEffect(() => {
    if (video?.processing_status === 'processing') {
      const interval = setInterval(() => refetch(), 3000)
      return () => clearInterval(interval)
    }
  }, [video?.processing_status, refetch])

  // Dynamic page title
  const displayTitle = video?.translated_title || video?.title
  useEffect(() => {
    if (displayTitle) {
      document.title = `${displayTitle} — Brevora`
    }
  }, [displayTitle])

  if (isLoading || !video) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  const toggleFavorite = () => {
    updateMeta.mutate({
      youtubeId: video.youtube_id,
      data: { is_favorite: !video.is_favorite },
    })
  }

  const handleRetry = () => {
    processMutation.mutate(video.youtube_id)
  }

  const formatDate = (d: string | null) => {
    if (!d) return ''
    return new Date(d).toLocaleDateString('zh-TW', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  return (
    <div id="main-content" className="min-h-screen bg-transparent">
      {/* Header */}
      <div className="glass-card-strong border-b border-slate-700/50">
        <div className="mx-auto max-w-4xl px-6 py-5">
          <div className="mb-3 flex items-center justify-between">
            <button
              onClick={() => navigate(-1)}
              aria-label="返回上一頁"
              className="flex items-center gap-1 text-sm text-slate-400 transition hover:text-slate-200"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 12H5M12 19l-7-7 7-7" />
              </svg>
              返回
            </button>
            <div className="flex items-center gap-2">
              <button
                onClick={toggleFavorite}
                aria-label={video.is_favorite ? '取消收藏' : '加入收藏'}
                className={`rounded-full p-2 transition hover:bg-slate-700/60 ${video.is_favorite ? 'text-amber-400' : 'text-slate-600'}`}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill={video.is_favorite ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                </svg>
              </button>
              <a
                href={`https://www.youtube.com/watch?v=${video.youtube_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 rounded-lg bg-slate-700 px-3 py-1.5 text-sm font-medium text-slate-300 transition hover:bg-slate-600"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
                  <polyline points="15 3 21 3 21 9" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
                觀看原片
              </a>
            </div>
          </div>
          <h1 className="text-xl font-bold text-white">{displayTitle}</h1>
          {video.translated_title && (
            <p className="mt-1 text-sm text-slate-400">{video.title}</p>
          )}
          <div className="mt-2 flex items-center gap-2 text-sm text-slate-400">
            <span>{video.channel_title}</span>
            <span>·</span>
            <span>{formatDate(video.published_at)}</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-4xl px-6 py-6">
        <section className="glass-card-strong rounded-xl border border-slate-700/50 p-6">
          <h2 className="mb-4 text-base font-semibold text-slate-200">節目筆記</h2>

          {video.processing_status === 'processing' || processMutation.isPending ? (
            <div className="flex flex-col items-center py-12 text-center">
              <LoadingSpinner className="mb-4" />
              <p className="text-sm text-slate-400">正在生成節目筆記，請稍候...</p>
              <p className="mt-1 text-xs text-slate-500">通常需要 10-30 秒</p>
            </div>
          ) : video.summary ? (
            <SummaryDisplay summary={video.summary} />
          ) : video.processing_status === 'error' ? (
            <div className="flex flex-col items-center py-12 text-center">
              <p className="mb-2 text-sm text-red-400">
                處理失敗{video.error_message ? `：${video.error_message}` : ''}
              </p>
              <button
                onClick={handleRetry}
                className="rounded-lg bg-blue-600/20 px-4 py-2 text-sm font-medium text-blue-400 transition hover:bg-blue-600/30"
              >
                重試
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center py-12 text-center">
              <p className="mb-3 text-sm text-slate-400">尚無筆記</p>
              <button
                onClick={handleRetry}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500"
              >
                生成筆記
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
