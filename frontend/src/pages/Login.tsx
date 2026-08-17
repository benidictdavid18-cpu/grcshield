import { useState } from 'react'

import { useAuth } from '../auth'

const DEMO = [
  { label: 'Auditor (read-only)', username: 'auditor', password: 'auditor-demo-2026' },
  { label: 'ISMS manager', username: 'isms.manager', password: 'manager-demo-2026' },
]

export function Login() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(username, password)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-shell">
      <div className="login-card">
        <h1>GRCShield</h1>
        <p className="card-meta">FinFlow Technologies · Information Security Management System</p>

        <form onSubmit={submit}>
          <label htmlFor="username">Username</label>
          <input
            id="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <button type="submit" className="primary" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="demo-block">
          <h2>Demo accounts</h2>
          <p className="muted">
            Published deliberately. This is a portfolio project holding fictional data for a
            fictional company; treating these as secrets would be theatre.
          </p>
          {DEMO.map((account) => (
            <button
              key={account.username}
              type="button"
              className="demo-fill"
              onClick={() => {
                setUsername(account.username)
                setPassword(account.password)
              }}
            >
              <strong>{account.label}</strong>
              <code>
                {account.username} / {account.password}
              </code>
            </button>
          ))}
          <p className="muted">
            The auditor account can read everything and change nothing — which is only
            meaningful because unauthenticated reads are refused outright.
          </p>
        </div>
      </div>
    </div>
  )
}
