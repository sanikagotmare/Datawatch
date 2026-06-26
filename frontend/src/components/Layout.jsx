import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import {
  LayoutDashboard, Upload, LogOut, Activity,
  GitBranch, AlertTriangle, Database, Zap
} from 'lucide-react'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const nav = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
      isActive ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'
    }`

  return (
    <div className="flex min-h-screen">
      <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col fixed h-full z-10">
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <Activity size={16} className="text-white"/>
            </div>
            <span className="font-bold text-lg">DataWatch</span>
          </div>
          <p className="text-xs text-gray-500 mt-1">AI Data Observability</p>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 mb-2">Overview</p>
          <NavLink to="/dashboard"   className={nav}><LayoutDashboard size={18}/> Dashboard</NavLink>

          <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 mt-4 mb-2">Data</p>
          <NavLink to="/upload"      className={nav}><Upload size={18}/> Upload Dataset</NavLink>
          <NavLink to="/datasources" className={nav}><Database size={18}/> Data Sources</NavLink>
          

          <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 mt-4 mb-2">AI Tools</p>
          <NavLink to="/heal"        className={nav}><Zap size={18}/> Self-Healing</NavLink>

          <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 mt-4 mb-2">Operations</p>
          <NavLink to="/incidents"   className={nav}><AlertTriangle size={18}/> Incidents</NavLink>
        </nav>

        <div className="p-4 border-t border-gray-800">
          <div className="flex items-center gap-3 px-2 py-2 mb-2">
            <div className="w-8 h-8 bg-indigo-700 rounded-full flex items-center justify-center text-sm font-bold">
              {user?.name?.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={() => { logout(); navigate('/login') }}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-red-400 transition-colors px-2 py-1 w-full">
            <LogOut size={16}/> Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 ml-64 p-8 min-h-screen">
        <Outlet />
      </main>
    </div>
  )
}
