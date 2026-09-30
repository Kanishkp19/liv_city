import { NavLink, Outlet } from 'react-router-dom'

const NAV = [
  { to: '/', label: 'Live City' },
  { to: '/jobs', label: 'Job Board' },
  { to: '/economy', label: 'Economy' },
  { to: '/replay', label: 'Replay' },
  { to: '/system', label: 'System' },
]

/** Left-rail shell + top bar per UIUX S2. */
export default function AppShell() {
  return (
    <div className="flex h-screen">
      <nav className="w-48 shrink-0 border-r border-border bg-surface p-3">
        <h1 className="mb-4 px-2 text-sm font-bold tracking-wide">AgentVille</h1>
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) =>
              `block rounded px-2 py-1.5 text-sm ${isActive ? 'bg-surface2 text-info' : 'text-dim hover:text-text'}`
            }
          >
            {n.label}
          </NavLink>
        ))}
      </nav>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 items-center gap-3 border-b border-border bg-surface px-4 text-xs text-dim">
          <span className="rounded bg-ok/20 px-2 py-0.5 text-ok">idle</span>
          <span>tick —</span>
          <span className="ml-auto font-mono">localhost:8000</span>
        </header>
        <main className="min-h-0 flex-1 overflow-auto p-4">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
