import { NavLink, Navigate, Route, Routes } from 'react-router-dom'

import { api } from './api'
import { useAuth } from './auth'
import { useAsync } from './useAsync'
import { Appetite } from './pages/Appetite'
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

  if (!session) return <Login />

  return (
    <div className="app">
      <DisclaimerBar />
      <header className="masthead">
        <div className="brand">
          <span className="brand-mark">GRCShield</span>
          <span className="brand-sub">FinFlow Technologies &middot; ISMS</span>
        </div>
        <nav>
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/executive">Executive</NavLink>
          <NavLink to="/risks">Risks</NavLink>
          <NavLink to="/soa">SoA</NavLink>
          <NavLink to="/testing">Testing</NavLink>
          <NavLink to="/isms">ISMS</NavLink>
          <NavLink to="/registers">Registers</NavLink>
          <NavLink to="/appetite">Appetite</NavLink>
          <NavLink to="/frameworks">Frameworks</NavLink>
          <NavLink to="/reports">Reports</NavLink>
        </nav>
        <div className="session">
          <span className="session-name">{session.fullName}</span>
          <span className={`role-chip ${session.canWrite ? '' : 'role-readonly'}`}>
            {session.canWrite ? session.role.replace('_', ' ').toLowerCase() : 'read-only'}
          </span>
          <button type="button" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>
      <main>
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
          <Route path="/appetite" element={<Appetite />} />
          <Route path="/frameworks" element={<Frameworks />} />
          <Route path="/controls" element={<ControlLibrary />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/roadmap" element={<Roadmap />} />
          <Route path="*" element={<p className="empty">Page not found.</p>} />
        </Routes>
      </main>
    </div>
  )
}
