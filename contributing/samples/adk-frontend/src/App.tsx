import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './contexts/AuthContext'
import { SupabaseProvider } from './contexts/SupabaseContext'
import { ThemeProvider } from './contexts/ThemeContext'

// Layouts
import MainLayout from './layouts/MainLayout'
import AuthLayout from './layouts/AuthLayout'

// Pages
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import LiveBoard from './pages/LiveBoard'
import VaultKeys from './pages/VaultKeys'
import TeamsSkills from './pages/TeamsSkills'
import Wallet from './pages/Wallet'
import Settings from './pages/Settings'
import DataMarketplace from './pages/DataMarketplace'

// Protected Route Component
import ProtectedRoute from './components/auth/ProtectedRoute'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <SupabaseProvider>
          <AuthProvider>
            <Router>
              <Routes>
                {/* Auth Routes */}
                <Route element={<AuthLayout />}>
                  <Route path="/login" element={<Login />} />
                </Route>

                {/* Protected Routes */}
                <Route element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/live-board" element={<LiveBoard />} />
                  <Route path="/data-marketplace" element={<DataMarketplace />} />
                  <Route path="/vault-keys" element={<VaultKeys />} />
                  <Route path="/teams-skills" element={<TeamsSkills />} />
                  <Route path="/wallet" element={<Wallet />} />
                  <Route path="/settings" element={<Settings />} />
                </Route>
              </Routes>
            </Router>
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: '#363636',
                  color: '#fff',
                },
                success: {
                  iconTheme: {
                    primary: '#10b981',
                    secondary: '#fff',
                  },
                },
                error: {
                  iconTheme: {
                    primary: '#ef4444',
                    secondary: '#fff',
                  },
                },
              }}
            />
          </AuthProvider>
        </SupabaseProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App