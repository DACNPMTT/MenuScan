import type { PropsWithChildren } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '@/app/providers/AuthProvider'
import { LanguageSync } from '@/app/providers/LanguageSync'
import { ToastProvider } from '@/app/providers/ToastProvider'

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <BrowserRouter>
      <AuthProvider>
        <LanguageSync />
        <ToastProvider>{children}</ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
