import { api, setToken, clearToken } from './api'
import { DEMO_MODE } from './demoMode'

export type CallbackResult = 'signed-in' | 'no-code' | 'expired'

// The backend sends a one-time code after #, never the JWT: the browser records this
// URL in its history before the page can erase it, so whatever is in it must be
// worthless once used. Read the code, wipe it from the address bar, trade it for the JWT
export async function handleCallback(): Promise<CallbackResult> {
  const code = new URLSearchParams(window.location.hash.slice(1)).get('code')
  window.history.replaceState(null, '', window.location.pathname)
  if (!code) return 'no-code'
  try {
    const { access_token } = await api.post<{ access_token: string }>('/auth/exchange', { code })
    setToken(access_token)
    return 'signed-in'
  } catch {
    // Already used (e.g. reopened from history) or older than 60 seconds
    return 'expired'
  }
}

export function logout() {
  clearToken()
  window.location.href = '/login'
}

export function isAuthenticated(): boolean {
  if (DEMO_MODE) return true
  return !!localStorage.getItem('token')
}
