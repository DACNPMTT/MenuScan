/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useState, useRef, useCallback, type ReactNode } from 'react'
import { apiRequest } from '@/shared/lib/api'

export interface User {
  id: string
  email: string
  display_name: string | null
  preferred_language: string
  role: string
}

interface AuthContextType {
  user: User | null
  accessToken: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  requestMagicLink: (email: string) => Promise<{ message: string; resend_after_seconds: number }>
  verifyMagicLink: (token: string) => Promise<User>
  setPassword: (password: string) => Promise<void>
  logout: () => Promise<void>
  refreshSession: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const isRefreshing = useRef(false)

  // Clear auth state locally
  const logoutState = useCallback(() => {
    setAccessToken(null)
    setUser(null)
  }, [])

  // Fetch current user details using access token
  const fetchCurrentUser = useCallback(async (token: string) => {
    try {
      const userData = await apiRequest<User>('/api/v1/auth/me', { token })
      setUser(userData)
    } catch (error) {
      console.error('Failed to fetch user profile', error)
      logoutState()
    }
  }, [logoutState])

  // Set auth state after successful login/verify
  const loginState = useCallback(async (token: string, userData?: User) => {
    setAccessToken(token)
    if (userData) {
      setUser(userData)
    } else {
      await fetchCurrentUser(token)
    }
    setLoading(false)
  }, [fetchCurrentUser])

  // 1. Login with Password
  const login = useCallback(async (email: string, password: string) => {
    const data = await apiRequest<{ access_token: string; user: User }>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    await loginState(data.access_token, data.user)
  }, [loginState])

  // 2. Request Magic Link
  const requestMagicLink = useCallback(async (email: string) => {
    return await apiRequest<{ message: string; resend_after_seconds: number }>('/api/v1/auth/magic-links', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  }, [])

  // 3. Verify Magic Link
  const verifyMagicLink = useCallback(async (token: string) => {
    const data = await apiRequest<{ access_token: string; user: User }>('/api/v1/auth/magic-links/verify', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
    await loginState(data.access_token, data.user)
    return data.user
  }, [loginState])

  // 4. Set Password
  const setPassword = useCallback(async (password: string) => {
    if (!accessToken) throw new Error('Unauthenticated')
    await apiRequest('/api/v1/auth/set-password', {
      method: 'POST',
      token: accessToken,
      body: JSON.stringify({ password }),
    })
  }, [accessToken])

  // 5. Logout
  const logout = useCallback(async () => {
    try {
      if (accessToken) {
        await apiRequest('/api/v1/auth/logout', {
          method: 'POST',
          token: accessToken,
        })
      }
    } catch (e) {
      console.error('Logout request failed', e)
    } finally {
      logoutState()
    }
  }, [accessToken, logoutState])

  // 6. Refresh Session (Silent refresh on reload)
  const refreshSession = useCallback(async () => {
    if (isRefreshing.current) return
    isRefreshing.current = true
    try {
      const data = await apiRequest<{ access_token: string }>('/api/v1/auth/refresh', {
        method: 'POST',
      })
      await loginState(data.access_token)
    } catch {
      // Refresh failed (no session or expired), log out silently
      logoutState()
    } finally {
      setLoading(false)
      isRefreshing.current = false
    }
  }, [loginState, logoutState])

  // Try to restore session on mount
  useEffect(() => {
    Promise.resolve().then(() => {
      refreshSession()
    })
  }, [refreshSession])

  return (
    <AuthContext.Provider
      value={{
        user,
        accessToken,
        loading,
        login,
        requestMagicLink,
        verifyMagicLink,
        setPassword,
        logout,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
