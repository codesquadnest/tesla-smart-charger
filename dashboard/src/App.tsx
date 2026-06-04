import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useStatus } from '@/hooks/useStatus'
import { MainLayout } from '@/components/layout/MainLayout'
import { FullPageSpinner } from '@/components/ui/Spinner'
import OnboardingPage from '@/pages/Onboarding/index'
import DashboardPage from '@/pages/Dashboard/index'
import VehiclesPage from '@/pages/Vehicles/index'
import HistoryPage from '@/pages/History/index'
import SettingsPage from '@/pages/Settings/index'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5_000,
      retry: 1,
    },
  },
})

function AppRoutes() {
  const { data: status, isLoading } = useStatus()

  if (isLoading) return <FullPageSpinner />

  // If not configured yet, show the onboarding wizard
  if (!status?.configured) {
    return (
      <Routes>
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="*" element={<Navigate to="/onboarding" replace />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/vehicles" element={<VehiclesPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      {/* Redirect away from onboarding if already configured */}
      <Route path="/onboarding" element={<Navigate to="/" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
