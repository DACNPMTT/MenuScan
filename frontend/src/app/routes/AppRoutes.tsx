import { Route, Routes } from 'react-router-dom'
import { AuthenticatedLayout } from '@/layouts/AuthenticatedLayout'
import { RequireGuest } from '@/app/routes/RequireGuest'
import { CheckEmailPage } from '@/pages/auth/CheckEmailPage'
import { LoginPage } from '@/pages/auth/LoginPage'
import { RegisterPage } from '@/pages/auth/RegisterPage'
import { VerifyPage } from '@/pages/auth/VerifyPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { LandingPage } from '@/pages/LandingPage'
import { MenusPage } from '@/pages/MenusPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { ScanResultPage } from '@/pages/ScanResultPage'
import { CameraScanPage } from '@/pages/CameraScanPage'
import { ScanPage } from '@/pages/ScanPage'
import { SetPasswordPage } from '@/pages/SetPasswordPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="auth/login" element={<RequireGuest><LoginPage /></RequireGuest>} />
      <Route path="auth/register" element={<RequireGuest><RegisterPage /></RequireGuest>} />
      <Route path="auth/check-email" element={<RequireGuest><CheckEmailPage /></RequireGuest>} />
      <Route path="auth/verify" element={<VerifyPage />} />
      <Route path="auth/set-password" element={<SetPasswordPage />} />

      <Route path="app" element={<AuthenticatedLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="scan/camera" element={<CameraScanPage />} />
        <Route path="scans/:scanId" element={<ScanResultPage />} />
        <Route path="scan" element={<ScanPage />} />
        <Route path="menus" element={<MenusPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
