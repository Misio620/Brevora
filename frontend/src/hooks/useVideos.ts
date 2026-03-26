import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

export interface VideoWithState {
  youtube_id: string
  channel_id: string
  title: string
  thumbnail: string | null
  published_at: string | null
  channel_title: string | null
  is_read: boolean
  is_favorite: boolean
  note: string
  processing_status: string
  summary: string | null
  translated_title: string | null
  error_message: string | null
}

interface FeedResponse {
  videos: VideoWithState[]
  total: number
  page: number
  per_page: number
  has_more: boolean
}

interface FeedParams {
  page?: number
  per_page?: number
  channel_id?: string
  status?: string
  favorites?: boolean
  search?: string
}

export function useVideoFeed(params: FeedParams = {}) {
  const query = new URLSearchParams()
  if (params.page) query.set('page', String(params.page))
  if (params.per_page) query.set('per_page', String(params.per_page))
  if (params.channel_id) query.set('channel_id', params.channel_id)
  if (params.status) query.set('status', params.status)
  if (params.favorites) query.set('favorites', 'true')
  if (params.search) query.set('search', params.search)

  return useQuery<FeedResponse>({
    queryKey: ['videos', 'feed', params],
    queryFn: () => api.get<FeedResponse>(`/videos/feed?${query}`),
    staleTime: 1000 * 60,
  })
}

export function useVideo(youtubeId: string) {
  return useQuery<VideoWithState>({
    queryKey: ['videos', youtubeId],
    queryFn: () => api.get<VideoWithState>(`/videos/${youtubeId}`),
    enabled: !!youtubeId,
  })
}

export function useUpdateMetadata() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ youtubeId, data }: { youtubeId: string; data: Record<string, unknown> }) =>
      api.patch<VideoWithState>(`/videos/${youtubeId}/metadata`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['videos'] })
    },
  })
}

export function useProcessVideo() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (youtubeId: string) =>
      api.post<{ status: string; youtube_id: string }>(`/videos/${youtubeId}/process`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['videos'] })
    },
  })
}

export function useSyncVideos() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<{ status: string; new_videos: number }>('/videos/sync'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['videos'] })
    },
  })
}
