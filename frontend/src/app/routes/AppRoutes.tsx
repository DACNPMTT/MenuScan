import { Route, Routes } from 'react-router-dom'
import { AuthenticatedLayout } from '@/layouts/AuthenticatedLayout'
import { RequireGuest } from '@/app/routes/RequireGuest'
import { RequireAuth } from '@/app/routes/RequireAuth'
import { CheckEmailPage } from '@/pages/auth/CheckEmailPage'
import { LoginPage } from '@/pages/auth/LoginPage'
import { RegisterPage } from '@/pages/auth/RegisterPage'
import { VerifyPage } from '@/pages/auth/VerifyPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { LandingPage } from '@/pages/LandingPage'
import { MenuDetailPage } from '@/pages/MenuDetailPage'
import { MenusPage } from '@/pages/MenusPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { ScanResultPage } from '@/pages/ScanResultPage'
import { CameraScanPage } from '@/pages/CameraScanPage'
import { ScanPage } from '@/pages/ScanPage'
import { SetPasswordPage } from '@/pages/SetPasswordPage'
import { OnboardingPage } from '@/pages/auth/OnboardingPage'
import { BillReceiptPage } from '@/pages/BillReceiptPage'
import { BillsPage } from '@/pages/BillsPage'
import { DiningSessionsPage } from '@/pages/dining/DiningSessionsPage'
import { HostDiningSessionPage } from '@/pages/dining/HostDiningSessionPage'
import { JoinDiningSessionPage } from '@/pages/dining/JoinDiningSessionPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="auth/login" element={<RequireGuest><LoginPage /></RequireGuest>} />
      <Route path="auth/register" element={<RequireGuest><RegisterPage /></RequireGuest>} />
      <Route path="auth/check-email" element={<RequireGuest><CheckEmailPage /></RequireGuest>} />
      <Route path="auth/verify" element={<VerifyPage />} />
      <Route path="auth/set-password" element={<SetPasswordPage />} />
      <Route path="auth/onboarding" element={<OnboardingPage />} />
      <Route path="app" element={<AuthenticatedLayout />}>
        {/* Guests can scan without an account; the rest requires sign-in. */}
        <Route index element={<RequireAuth><DashboardPage /></RequireAuth>} />
        <Route path="scan" element={<ScanPage />} />
        <Route path="scan/camera" element={<CameraScanPage />} />
        <Route path="scans/:scanId" element={<ScanResultPage />} />
        <Route path="menus" element={<RequireAuth><MenusPage /></RequireAuth>} />
        <Route path="menus/:menuId" element={<RequireAuth><MenuDetailPage /></RequireAuth>} />
        <Route path="bills" element={<RequireAuth><BillsPage /></RequireAuth>} />
        <Route path="bills/:billId" element={<RequireAuth><BillReceiptPage /></RequireAuth>} />
        <Route path="profile" element={<RequireAuth><ProfilePage /></RequireAuth>} />
        <Route path="dining" element={<RequireAuth><DiningSessionsPage /></RequireAuth>} />
        <Route path="dining/sessions/:sessionId" element={<RequireAuth><HostDiningSessionPage /></RequireAuth>} />
      </Route>
      <Route path="dining/join" element={<JoinDiningSessionPage />} />

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
