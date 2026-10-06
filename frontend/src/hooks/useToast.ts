import { createContext, useContext } from 'react'

export type ToastType = 'success' | 'error' | 'info'

interface ToastContextType {
  toast: (message: string, type?: ToastType) => void
}

export const ToastContext = createContext<ToastContextType>({ toast: () => {} })

export function useToast() {
  return useContext(ToastContext)
}
