import { setToken, clearToken } from './api'

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
  return !!localStorage.getItem('token')
}
