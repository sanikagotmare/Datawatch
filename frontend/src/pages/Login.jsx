import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Activity } from 'lucide-react'

export default function Login() {
  const [form, setForm] = useState({ email:'', password:'' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate  = useNavigate()

  const submit = async (e) => {
    e.preventDefault(); setLoading(true); setError('')
    try { await login(form.email, form.password); navigate('/dashboard') }
    catch (err) { setError(err.response?.data?.detail || 'Login failed') }
    finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center mx-auto mb-4"><Activity size={24} className="text-white"/></div>
          <h1 className="text-2xl font-bold">Welcome to DataWatch</h1>
          <p className="text-gray-400 mt-1">AI-powered data observability · 100% Python</p>
        </div>
        <div className="card">
          <h2 className="text-lg font-semibold mb-6">Sign in</h2>
          {error && <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-lg px-4 py-3 mb-4">{error}</div>}
          <form onSubmit={submit} className="space-y-4">
            <div><label className="block text-sm text-gray-400 mb-1.5">Email</label><input className="input" type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})} required/></div>
            <div><label className="block text-sm text-gray-400 mb-1.5">Password</label><input className="input" type="password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} required/></div>
            <button type="submit" className="btn-primary w-full mt-2" disabled={loading}>{loading?'Signing in...':'Sign in'}</button>
          </form>
          <p className="text-sm text-gray-500 text-center mt-4">No account? <Link to="/register" className="text-indigo-400">Register</Link></p>
        </div>
      </div>
    </div>
  )
}
