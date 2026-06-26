import { createContext, useContext, useState, useEffect } from 'react'
import { authApi } from '../services/api'

const Ctx = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (localStorage.getItem('token')) {
      authApi.me().then(r => setUser(r.data)).catch(() => localStorage.removeItem('token')).finally(() => setLoading(false))
    } else { setLoading(false) }
  }, [])

  const login    = async (email, password) => { const r = await authApi.login({ email, password }); localStorage.setItem('token', r.data.token); setUser(r.data); return r.data }
  const register = async (email, password, name) => { const r = await authApi.register({ email, password, name }); localStorage.setItem('token', r.data.token); setUser(r.data); return r.data }
  const logout   = () => { localStorage.removeItem('token'); setUser(null) }

  return <Ctx.Provider value={{ user, login, register, logout, loading }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
