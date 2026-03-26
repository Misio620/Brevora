import { createContext, useContext } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'

export interface UserInfo {
  id: string
  email: string
  display_name: string | null
  avatar_url: string | null
}

interface AuthContextType {
  user: UserInfo | null
  isLoading: boolean
  isAuthenticated: boolean
}

export const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
})

export function useAuth() {
  return useContext(AuthContext)
}

export function useAuthQuery() {
  return useQuery<UserInfo>({
    queryKey: ['auth', 'me'],
    queryFn: () => api.get<UserInfo>('/auth/me'),
    enabled: isAuthenticated(),
    retry: false,
    staleTime: 1000 * 60 * 5,
  })
}
