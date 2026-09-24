import { setToken, clearToken } from './api'
import { DEMO_MODE } from './demoMode'

export function handleCallback(): string | null {
  const params = new URLSearchParams(window.location.search)
  const token = params.get('token')
  if (token) {
    setToken(token)
    return token
  }
  return null
}

export function logout() {
  clearToken()
  window.location.href = '/login'
}

export function isAuthenticated(): boolean {
  if (DEMO_MODE) return true
  return !!localStorage.getItem('token')
}
