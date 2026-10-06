import { setToken, clearToken } from './api'
import { DEMO_MODE } from './demoMode'

// The backend puts the JWT after # so it never reaches a server log; read it,
// then wipe it from the address bar and this history entry right away
export function handleCallback(): string | null {
  const token = new URLSearchParams(window.location.hash.slice(1)).get('token')
  window.history.replaceState(null, '', window.location.pathname)
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
