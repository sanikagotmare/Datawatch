import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import Login         from './pages/Login'
import Register      from './pages/Register'
import Dashboard     from './pages/Dashboard'
import Upload        from './pages/Upload'
import Report        from './pages/Report'

import Incidents     from './pages/Incidents'
import IncidentDetail from './pages/IncidentDetail'
import DataSources   from './pages/DataSources'
import SelfHeal      from './pages/SelfHeal'
import Layout        from './components/Layout'

function Guard({ children }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"/>
    </div>
  )
  return user ? children : <Navigate to="/login" />
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login"    element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<Guard><Layout /></Guard>}>
            <Route index element={<Navigate to="/dashboard" />} />
            <Route path="dashboard"       element={<Dashboard />} />
            <Route path="upload"          element={<Upload />} />
            <Route path="report/:id"      element={<Report />} />
           
            <Route path="incidents"       element={<Incidents />} />
            <Route path="incidents/:id"   element={<IncidentDetail />} />
            <Route path="datasources"     element={<DataSources />} />
            <Route path="heal"            element={<SelfHeal />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
