import { Route, Routes } from 'react-router-dom'
import { AuthenticatedLayout } from '@/layouts/AuthenticatedLayout'
import { PublicLayout } from '@/layouts/PublicLayout'
import { AuthVerifyPage } from '@/pages/AuthVerifyPage'
import { LoginPage } from '@/pages/LoginPage'
import { SetPasswordPage } from '@/pages/SetPasswordPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { HomePage } from '@/pages/HomePage'
import { MenusPage } from '@/pages/MenusPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { ScanPage } from '@/pages/ScanPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<HomePage />} />
        <Route path="auth/login" element={<LoginPage />} />
        <Route path="auth/verify" element={<AuthVerifyPage />} />
        <Route path="auth/set-password" element={<SetPasswordPage />} />
      </Route>

      <Route path="app" element={<AuthenticatedLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="scan" element={<ScanPage />} />
        <Route path="menus" element={<MenusPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
