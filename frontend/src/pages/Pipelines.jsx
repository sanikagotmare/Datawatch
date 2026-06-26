import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { pipelineApi } from '../services/api'
import { GitBranch, Plus, Play, ChevronRight, CheckCircle, AlertTriangle, XCircle, X } from 'lucide-react'

const S_ICON  = { HEALTHY:CheckCircle, WARNING:AlertTriangle, FAILED:XCircle }
const S_COLOR = { HEALTHY:'text-green-400', WARNING:'text-yellow-400', FAILED:'text-red-400' }
const S_BG    = { HEALTHY:'bg-green-500/10', WARNING:'bg-yellow-500/10', FAILED:'bg-red-500/10' }

export default function Pipelines() {
  const [pipelines,  setPipelines]  = useState([])
  const [loading,    setLoading]    = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form,       setForm]       = useState({ name:'', description:'' })
  const [creating,   setCreating]   = useState(false)
  const [runningId,  setRunningId]  = useState(null)
  const [error,      setError]      = useState('')

  const load = () => pipelineApi.list().then(r => setPipelines(r.data)).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return
    setCreating(true); setError('')
    try { await pipelineApi.create(form); setForm({ name:'', description:'' }); setShowCreate(false); load() }
    catch (err) { setError(err.response?.data?.detail || 'Failed to create pipeline') }
    finally { setCreating(false) }
  }

  const triggerRun = async (e, id) => {
    e.preventDefault(); e.stopPropagation()
    setRunningId(id)
    try { await pipelineApi.triggerRun(id); load() } finally { setRunningId(null) }
  }

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"/></div>

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold">Pipelines</h1><p className="text-gray-400 mt-0.5">Monitor and manage your data pipelines</p></div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2"><Plus size={16}/> New Pipeline</button>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-semibold text-lg">Create Pipeline</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-500 hover:text-gray-300"><X size={20}/></button>
            </div>
            {error && <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-lg px-4 py-3 mb-4">{error}</div>}
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Pipeline name *</label>
                <input className="input" placeholder="e.g. Sales Data Pipeline" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required/>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Description</label>
                <textarea className="input resize-none" rows={3} placeholder="What does this pipeline process?" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}/>
              </div>
              <div className="flex gap-3 pt-1">
                <button type="submit" className="btn-primary flex-1" disabled={creating}>{creating ? 'Creating...' : 'Create Pipeline'}</button>
                <button type="button" className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {pipelines.length === 0 ? (
        <div className="card text-center py-16">
          <GitBranch size={40} className="mx-auto mb-3 text-gray-700"/>
          <p className="text-gray-400 font-medium">No pipelines yet</p>
          <p className="text-gray-600 text-sm mt-1 mb-4">Create a pipeline to start automated hourly monitoring</p>
          <button onClick={() => setShowCreate(true)} className="btn-primary mx-auto">Create your first pipeline</button>
        </div>
      ) : (
        <div className="space-y-3">
          {pipelines.map(p => {
            const Icon = S_ICON[p.status] || CheckCircle
            return (
              <Link key={p.id} to={`/pipelines/${p.id}`} className="card flex items-center gap-4 hover:border-gray-700 transition-colors group p-4">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${S_BG[p.status]}`}>
                  <Icon size={18} className={S_COLOR[p.status]}/>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-gray-100">{p.name}</p>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${S_BG[p.status]} ${S_COLOR[p.status]}`}>{p.status}</span>
                  </div>
                  {p.description && <p className="text-sm text-gray-500 truncate mt-0.5">{p.description}</p>}
                  <div className="flex gap-4 mt-1 text-xs text-gray-600">
                    <span>✓ {p.successfulRuns} runs</span>
                    <span>✗ {p.failedRuns} failed</span>
                    {p.lastRunAt && <span>Last: {new Date(p.lastRunAt).toLocaleString()}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="text-right">
                    <p className="text-lg font-bold">{p.healthScore}%</p>
                    <p className="text-xs text-gray-600">health</p>
                  </div>
                  <button onClick={e => triggerRun(e, p.id)} className="btn-secondary flex items-center gap-1.5 text-xs px-3 py-1.5" disabled={runningId === p.id}>
                    <Play size={12}/>{runningId === p.id ? 'Running...' : 'Run'}
                  </button>
                  <ChevronRight size={16} className="text-gray-600 group-hover:text-gray-400"/>
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
