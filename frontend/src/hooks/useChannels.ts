import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

export interface ChannelInfo {
  id: string
  title: string
  thumbnail: string | null
}

export interface PinnedChannel {
  id: string
  channel_id: string
  title: string | null
  thumbnail: string | null
}

export function useSubscriptions() {
  return useQuery<ChannelInfo[]>({
    queryKey: ['channels', 'subscriptions'],
    queryFn: () => api.get<ChannelInfo[]>('/channels/subscriptions'),
    staleTime: 1000 * 60 * 5,
  })
}

export function usePinnedChannels() {
  return useQuery<PinnedChannel[]>({
    queryKey: ['channels', 'pinned'],
    queryFn: () => api.get<PinnedChannel[]>('/channels/pinned'),
    staleTime: 1000 * 60,
  })
}

export function usePinChannel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ channelId, title, thumbnail }: { channelId: string; title?: string; thumbnail?: string }) =>
      api.post(`/channels/pin/${channelId}`, { title, thumbnail }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels', 'pinned'] })
      queryClient.invalidateQueries({ queryKey: ['videos', 'feed'] })
    },
  })
}

export function useUnpinChannel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (channelId: string) => api.delete(`/channels/unpin/${channelId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels', 'pinned'] })
      queryClient.invalidateQueries({ queryKey: ['videos', 'feed'] })
    },
  })
}
