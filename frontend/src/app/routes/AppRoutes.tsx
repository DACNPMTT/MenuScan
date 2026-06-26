import { Route, Routes } from 'react-router-dom'
import { AuthenticatedLayout } from '@/layouts/AuthenticatedLayout'
<<<<<<< HEAD
import { CheckEmailPage } from '@/pages/auth/CheckEmailPage'
import { LoginPage } from '@/pages/auth/LoginPage'
import { RegisterPage } from '@/pages/auth/RegisterPage'
import { VerifyPage } from '@/pages/auth/VerifyPage'
=======
import { PublicLayout } from '@/layouts/PublicLayout'
import { AuthVerifyPage } from '@/pages/AuthVerifyPage'
import { LoginPage } from '@/pages/LoginPage'
import { SetPasswordPage } from '@/pages/SetPasswordPage'
>>>>>>> 8e3ffc0ab76eefce856d544cf59b2eb07e49acca
import { DashboardPage } from '@/pages/DashboardPage'
import { LandingPage } from '@/pages/LandingPage'
import { MenusPage } from '@/pages/MenusPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { ScanPage } from '@/pages/ScanPage'

export function AppRoutes() {
  return (
    <Routes>
<<<<<<< HEAD
      <Route path="/" element={<LandingPage />} />
      <Route path="auth/login" element={<LoginPage />} />
      <Route path="auth/register" element={<RegisterPage />} />
      <Route path="auth/check-email" element={<CheckEmailPage />} />
      <Route path="auth/verify" element={<VerifyPage />} />
=======
      <Route element={<PublicLayout />}>
        <Route index element={<HomePage />} />
        <Route path="auth/login" element={<LoginPage />} />
        <Route path="auth/verify" element={<AuthVerifyPage />} />
        <Route path="auth/set-password" element={<SetPasswordPage />} />
      </Route>
>>>>>>> 8e3ffc0ab76eefce856d544cf59b2eb07e49acca

      <Route path="app" element={<AuthenticatedLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="scan" element={<ScanPage />} />
        <Route path="menus" element={<MenusPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
