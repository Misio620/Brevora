// Kept apart from demo.ts so production builds never bundle the demo dataset
export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true'
export const DEMO_STORAGE_KEY = 'brevora-demo-state'

export function resetDemo() {
  try {
    localStorage.removeItem(DEMO_STORAGE_KEY)
  } catch {
    // Storage blocked: nothing was saved
  }
  window.location.href = '/'
}
