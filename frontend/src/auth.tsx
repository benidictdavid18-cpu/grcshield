import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

export interface Session {
  token: string
  username: string
  fullName: string
  role: string
  canWrite: boolean
}

const STORAGE_KEY = 'grcshield.session'

interface AuthValue {
  session: Session | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

function read(): Session | null {
  // sessionStorage, not localStorage: the token dies with the tab rather than
  // persisting on a shared machine.
  const raw = sessionStorage.getItem(STORAGE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as Session
  } catch {
    sessionStorage.removeItem(STORAGE_KEY)
    return null
  }
}

let currentToken: string | null = read()?.token ?? null

/** Read by the API client so every request carries the bearer token. */
export function getToken(): string | null {
  return currentToken
}

let onUnauthorised: (() => void) | null = null

/** Called by the API client on a 401, so an expired token returns to the login screen
 *  instead of leaving the page silently empty. */
export function handleUnauthorised(): void {
  onUnauthorised?.()
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(read)

  const logout = useCallback(() => {
    sessionStorage.removeItem(STORAGE_KEY)
    currentToken = null
    setSession(null)
  }, [])

  // Registered in an effect, not during render: assigning a module global while
  // rendering is a side effect React may run twice in development, and the value
  // would be stale if the provider ever re-rendered with a different logout.
  useEffect(() => {
    onUnauthorised = logout
    return () => {
      onUnauthorised = null
    }
  }, [logout])

  const login = useCallback(async (username: string, password: string) => {
    const response = await fetch('/api/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!response.ok) {
      if (response.status === 401) throw new Error('Incorrect username or password.')
      // A 429 carries how long to wait; show the API's sentence rather than a code.
      let detail: string | null = null
      try {
        detail = (await response.json()).detail ?? null
      } catch {
        /* not JSON */
      }
      throw new Error(typeof detail === 'string' ? detail : `Sign-in failed (${response.status}).`)
    }
    const body = await response.json()
    const next: Session = {
      token: body.access_token,
      username: body.username,
      fullName: body.full_name,
      role: body.role,
      canWrite: body.can_write,
    }
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    currentToken = next.token
    setSession(next)
  }, [])

  const value = useMemo(() => ({ session, login, logout }), [session, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
