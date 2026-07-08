/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { apiRequest } from '@/shared/lib/api'
import {
  getAccessToken,
  setAccessToken as setStoredAccessToken,
  clearAccessToken as clearStoredAccessToken,
  refreshAccessToken,
  setAuthFailureHandler,
} from '@/shared/lib/auth-token'

export interface User {
  id: string
  email: string
  display_name: string | null
  preferred_language: string
  allergies: string[]
  dietary_preferences: string[]
  role: string
  status?: string
  created_at?: string
}

export interface UpdateProfilePayload {
  display_name?: string | null
  preferred_language?: string
  allergies?: string[]
  dietary_preferences?: string[]
}

interface AuthContextType {
  user: User | null
  accessToken: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  requestMagicLink: (email: string) => Promise<{ message: string; resend_after_seconds: number }>
  verifyMagicLink: (token: string) => Promise<User>
  setPassword: (password: string) => Promise<void>
  updateProfile: (payload: UpdateProfilePayload) => Promise<User>
  logout: () => Promise<void>
  refreshSession: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  // Clear auth state locally. Clear the manager token first so the manager and
  // React state stay in sync.
  const logoutState = useCallback(() => {
    clearStoredAccessToken()
    setAccessToken(null)
    setUser(null)
  }, [])

  // Fetch current user details using access token. apiRequest auto-refreshes on
  // 401; if refresh truly failed, the authFailureHandler already cleared state.
  // A non-auth 5xx must NOT log the user out, so we no longer call logoutState()
  // here.
  const fetchCurrentUser = useCallback(async (token: string) => {
    try {
      const userData = await apiRequest<User>('/api/v1/auth/me', { token })
      setUser(userData)
    } catch (error) {
      console.error('Failed to fetch user profile', error)
    }
  }, [])
  // Set auth state after successful login/verify
  const loginState = useCallback(async (token: string, userData?: User) => {
    setStoredAccessToken(token)
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
    // Read the manager's token, not the React state copy — the state copy can
    // lag behind a silent/401-triggered refresh (see refreshSession/mount effect).
    const token = getAccessToken()
    if (!token) throw new Error('Unauthenticated')
    await apiRequest('/api/v1/auth/set-password', {
      method: 'POST',
      token,
      body: JSON.stringify({ password }),
    })
  }, [])

  const updateProfile = useCallback(async (payload: UpdateProfilePayload) => {
    if (!accessToken) throw new Error('Unauthenticated')
    const updatedUser = await apiRequest<User>('/api/v1/auth/me/profile', {
      method: 'POST',
      token: accessToken,
      body: JSON.stringify(payload),
    })
    setUser(updatedUser)
    return updatedUser
  }, [accessToken])

  // 5. Logout
  const logout = useCallback(async () => {
    try {
      // Same reasoning as setPassword: use the manager's token so logout still
      // calls the backend (and actually revokes the session) even when the
      // session was restored via silent refresh rather than an explicit login.
      const token = getAccessToken()
      if (token) {
        await apiRequest('/api/v1/auth/logout', {
          method: 'POST',
          token,
        })
      }
    } catch (e) {
      console.error('Logout request failed', e)
    } finally {
      logoutState()
    }
  }, [logoutState])

  // 6. Refresh Session — delegates to the token manager (single-flight, raw
  // fetch so it never recurses into apiRequest). Kept on the context for
  // future callers; the mount effect and 401 auto-refresh go through the manager.
  const refreshSession = useCallback(async () => {
    const token = await refreshAccessToken()
    if (token) {
      setAccessToken(token)
      await fetchCurrentUser(token)
      setLoading(false)
    } else {
      logoutState()
      setLoading(false)
    }
  }, [fetchCurrentUser, logoutState])

  // Restore session on mount via the token manager. Register the failure
  // handler so any refresh failure (e.g. expired/missing cookie) clears auth
  // state and ends the loading state. Skip the silent refresh on the magic-link
  // verify route: VerifyPage exchanges the token and establishes the session
  // itself — firing refresh here races verify (the refresh request leaves
  // before verify's Set-Cookie lands, returns 401, and the failure handler
  // would clobber the session VerifyPage is building).
  useEffect(() => {
    setAuthFailureHandler(() => {
      logoutState()
      setLoading(false)
    })
    const isVerifyRoute = window.location.pathname.startsWith('/auth/verify')
    // Deferred to a microtask so setLoading runs outside the effect body
    // (synchronous setState in an effect is flagged by react-hooks rules).
    void Promise.resolve().then(async () => {
      if (isVerifyRoute) {
        setLoading(false)
        return
      }
      const token = await refreshAccessToken()
      if (token) {
        setAccessToken(token)
        await fetchCurrentUser(token)
      }
      setLoading(false)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        updateProfile,
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
