import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthContext, useAuthQuery } from '@/hooks/useAuth'
import { ToastProvider } from '@/components/common/Toast'
import { isAuthenticated } from '@/lib/auth'
import { DEMO_MODE } from '@/lib/demoMode'
import LoginPage from '@/pages/LoginPage'
import CallbackPage from '@/pages/CallbackPage'
import DashboardPage from '@/pages/DashboardPage'
import VideoDetailPage from '@/pages/VideoDetailPage'
import LoadingSpinner from '@/components/common/LoadingSpinner'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data: user, isLoading } = useAuthQuery()

  if (isAuthenticated() && isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <AuthContext.Provider
      value={{
        user: user || null,
        isLoading,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-lg focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white"
          >
            跳到主要內容
          </a>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={DEMO_MODE ? <Navigate to="/" replace /> : <LoginPage />} />
              <Route path="/callback" element={DEMO_MODE ? <Navigate to="/" replace /> : <CallbackPage />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/video/:id"
                element={
                  <ProtectedRoute>
                    <VideoDetailPage />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </AuthProvider>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  )
}
