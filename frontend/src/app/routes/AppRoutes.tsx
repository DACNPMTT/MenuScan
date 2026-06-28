import { Route, Routes } from 'react-router-dom'
import { AuthenticatedLayout } from '@/layouts/AuthenticatedLayout'
import { CheckEmailPage } from '@/pages/auth/CheckEmailPage'
import { LoginPage } from '@/pages/auth/LoginPage'
import { RegisterPage } from '@/pages/auth/RegisterPage'
import { VerifyPage } from '@/pages/auth/VerifyPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { LandingPage } from '@/pages/LandingPage'
import { MenusPage } from '@/pages/MenusPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { ScanPage } from '@/pages/ScanPage'
import { SetPasswordPage } from '@/pages/SetPasswordPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="auth/login" element={<LoginPage />} />
      <Route path="auth/register" element={<RegisterPage />} />
      <Route path="auth/check-email" element={<CheckEmailPage />} />
      <Route path="auth/verify" element={<VerifyPage />} />
      <Route path="auth/set-password" element={<SetPasswordPage />} />

      <Route path="app" element={<AuthenticatedLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="scan" element={<ScanPage />} />
        <Route path="menus" element={<MenusPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
