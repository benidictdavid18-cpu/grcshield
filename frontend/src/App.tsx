import { Operations } from './pages/Operations'
import { useEffect, useState } from 'react'
import { RecordDrawer } from './RecordDrawer'
import { NavLink, Navigate, Route, Routes, useLocation, useSearchParams } from 'react-router-dom'

import { AiStatusChip } from './AiAssistant'
import { api } from './api'
import { useAuth } from './auth'
import { useAsync } from './useAsync'
import { Appetite } from './pages/Appetite'
import { Consistency } from './pages/Consistency'
import { ControlLibrary } from './pages/ControlLibrary'
import { Dashboard } from './pages/Dashboard'
import { Executive } from './pages/Executive'
import { Frameworks } from './pages/Frameworks'
import { ISMS } from './pages/ISMS'
import { Login } from './pages/Login'
import { Registers } from './pages/Registers'
import { Reports } from './pages/Reports'
import { RiskDetail } from './pages/RiskDetail'
import { RiskRegister } from './pages/RiskRegister'
import { Roadmap } from './pages/Roadmap'
import { SoA } from './pages/SoA'
import { Testing } from './pages/Testing'

function DisclaimerBar() {
  const { data } = useAsync(() => api.health(), [])
  return (
    <div className="disclaimer" role="note">
      <strong>Sample / Portfolio Assessment.</strong> FinFlow Technologies is a fictional company.
      No certification body or audit firm has assessed this data.
      {data && !data.seeded && (
        <span className="disclaimer-warning">
          {' '}
          Seed data incomplete: {data.annex_a_controls}/{data.annex_a_expected} Annex A controls
          loaded.
        </span>
      )}
    </div>
  )
}

export function App() {
  const { session, logout } = useAuth()
  const location = useLocation()
  const [params, setParams] = useSearchParams()
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem('grc-theme') ?? 'light'
    } catch {
      return 'light'
    }
  })
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem('grc-theme', theme)
    } catch {
      /* Storage is optional. */
    }
  }, [theme])
  const closeRecord = () =>
    setParams(
      (old) => {
        const next = new URLSearchParams(old)
        next.delete('record')
        next.delete('retry')
        return next
      },
      { replace: true },
    )

  if (!session) return <Login />

  return (
    <div
      className="app"
      onClickCapture={(event) => {
        if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)
          return
        const link = (event.target as HTMLElement).closest('a')
        if (!link || link.hasAttribute('data-navigation')) return
        const url = new URL(link.href)
        if (url.origin !== window.location.origin) return
        const risk = url.pathname.match(/^\/risks\/([^/]+)$/)
        const record = url.searchParams.get('record') ?? (risk ? decodeURIComponent(risk[1]) : null)
        if (!record) return
        event.preventDefault()
        event.stopPropagation()
        setParams((old) => {
          const next = new URLSearchParams(old)
          next.set('record', record)
          next.delete('retry')
          return next
        })
      }}
    >
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <DisclaimerBar />
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-symbol" aria-hidden="true">
            ◇
          </span>
          <span className="brand-mark">
            GRCShield<span className="brand-dot">.</span>
          </span>
          <span className="brand-sub">FinFlow / Governance workspace</span>
        </div>
        <span className="nav-caption">Workspace</span>
        <nav aria-label="Primary navigation">
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/executive">Executive</NavLink>
          <NavLink to="/risks">Risks</NavLink>
          <NavLink to="/soa">SoA</NavLink>
          <NavLink to="/testing">Testing</NavLink>
          <NavLink to="/isms">ISMS</NavLink>
          <NavLink to="/registers">Registers</NavLink>
          <NavLink to="/operations">Operations</NavLink>
          <NavLink to="/consistency">Consistency</NavLink>
          <NavLink to="/appetite">Appetite</NavLink>
          <NavLink to="/frameworks">Frameworks</NavLink>
          <NavLink to="/reports">Reports</NavLink>
        </nav>
        <div className="sidebar-note">
          <span className="eyebrow">Built on evidence</span>
          <p>
            Every control.
            <br />
            Every decision.
            <br />
            One connected view.
          </p>
          <span className="sidebar-edition">PORTFOLIO / 2026</span>
        </div>
      </aside>
      <header className="masthead">
        <div className="workspace-location">
          <span>Workspace</span>
          <span aria-hidden="true">/</span>
          <strong>{location.pathname.split('/')[1]?.replace(/-/g, ' ') || 'Dashboard'}</strong>
        </div>
        <div className="session">
          <button
            type="button"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          >
            {theme === 'dark' ? 'Light theme' : 'Dark theme'}
          </button>
          <AiStatusChip />
          <span className="session-name">{session.fullName}</span>
          <span className={`role-chip ${session.canWrite ? '' : 'role-readonly'}`}>
            {session.canWrite ? session.role.replace('_', ' ').toLowerCase() : 'read-only'}
          </span>
          <button type="button" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>
      <main id="main-content" tabIndex={-1}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/executive" element={<Executive />} />
          <Route path="/risks" element={<RiskRegister />} />
          <Route path="/risks/:riskRef" element={<RiskDetail />} />
          <Route path="/soa" element={<SoA />} />
          <Route path="/testing" element={<Testing />} />
          <Route path="/isms" element={<ISMS />} />
          <Route path="/registers" element={<Registers />} />
          <Route path="/operations" element={<Operations />} />
          <Route path="/consistency" element={<Consistency />} />
          <Route path="/appetite" element={<Appetite />} />
          <Route path="/frameworks" element={<Frameworks />} />
          <Route path="/controls" element={<ControlLibrary />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/roadmap" element={<Roadmap />} />
          <Route path="*" element={<p className="empty">Page not found.</p>} />
        </Routes>
      </main>
      {params.get('record') && (
        <RecordDrawer
          key={params.get('record')}
          record={params.get('record')!}
          onClose={closeRecord}
        />
      )}
    </div>
  )
}
