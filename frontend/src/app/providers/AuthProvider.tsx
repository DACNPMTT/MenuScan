import { createContext, useContext, useEffect, useState, useRef, type ReactNode } from 'react'
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
  requestMagicLink: (email: string) => Promise<{ message: string; resend_after_seconds: int }>
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

  // Fetch current user details using access token
  const fetchCurrentUser = async (token: string) => {
    try {
      const userData = await apiRequest<User>('/api/v1/auth/me', { token })
      setUser(userData)
    } catch (error) {
      console.error('Failed to fetch user profile', error)
      logoutState()
    }
  }

  // Set auth state after successful login/verify
  const loginState = async (token: string, userData?: User) => {
    setAccessToken(token)
    if (userData) {
      setUser(userData)
    } else {
      await fetchCurrentUser(token)
    }
  }

  // Clear auth state locally
  const logoutState = () => {
    setAccessToken(null)
    setUser(null)
  }

  // 1. Login with Password
  const login = async (email: string, password: string) => {
    const data = await apiRequest<{ access_token: string; user: User }>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    await loginState(data.access_token, data.user)
  }

  // 2. Request Magic Link
  const requestMagicLink = async (email: string) => {
    return await apiRequest<{ message: string; resend_after_seconds: number }>('/api/v1/auth/magic-links', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  }

  // 3. Verify Magic Link
  const verifyMagicLink = async (token: string) => {
    const data = await apiRequest<{ access_token: string; user: User }>('/api/v1/auth/magic-links/verify', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
    await loginState(data.access_token, data.user)
    return data.user
  }

  // 4. Set Password
  const setPassword = async (password: string) => {
    if (!accessToken) throw new Error('Unauthenticated')
    await apiRequest('/api/v1/auth/set-password', {
      method: 'POST',
      token: accessToken,
      body: JSON.stringify({ password }),
    })
  }

  // 5. Logout
  const logout = async () => {
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
  }

  const isRefreshing = useRef(false)

  // 6. Refresh Session (Silent refresh on reload)
  const refreshSession = async () => {
    if (isRefreshing.current) return
    isRefreshing.current = true
    try {
      const data = await apiRequest<{ access_token: string }>('/api/v1/auth/refresh', {
        method: 'POST',
      })
      await loginState(data.access_token)
    } catch (e) {
      // Refresh failed (no session or expired), log out silently
      logoutState()
    } finally {
      setLoading(false)
      isRefreshing.current = false
    }
  }

  // Try to restore session on mount
  useEffect(() => {
    refreshSession()
  }, [])

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
