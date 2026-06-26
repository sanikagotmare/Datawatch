import { useState } from 'react'
import { connectorApi } from '../services/api'
import { Database, Globe, CheckCircle, XCircle, Plug, Trash2, TestTube } from 'lucide-react'

const TYPES = [
  { value:'postgresql', label:'PostgreSQL', icon:'🐘', placeholder_url:'postgresql://user:pass@localhost:5432/mydb', placeholder_q:'SELECT * FROM your_table LIMIT 1000' },
  { value:'mysql',      label:'MySQL',      icon:'🐬', placeholder_url:'mysql+pymysql://user:pass@localhost:3306/mydb', placeholder_q:'SELECT * FROM your_table LIMIT 1000' },
  { value:'sqlite',     label:'SQLite',     icon:'📁', placeholder_url:'sqlite:///./path/to/file.db', placeholder_q:'SELECT * FROM your_table LIMIT 1000' },
  { value:'api',        label:'REST API',   icon:'🌐', placeholder_url:'https://api.example.com', placeholder_q:'/v1/data/endpoint' },
]

const STATUS_STYLE = {
  CONNECTED:      'text-green-400 bg-green-500/10 border-green-500/20',
  ERROR:          'text-red-400 bg-red-500/10 border-red-500/20',
  NOT_CONFIGURED: 'text-gray-400 bg-gray-500/10 border-gray-500/20',
}

export default function ConnectorPanel({ pipeline, onUpdated }) {
  const [type,    setType]    = useState(pipeline.connectorType || 'postgresql')
  const [url,     setUrl]     = useState('')
  const [query,   setQuery]   = useState('')
  const [saving,  setSaving]  = useState(false)
  const [testing, setTesting] = useState(false)
  const [preview, setPreview] = useState(null)
  const [msg,     setMsg]     = useState(null)  // { text, ok }
  const [editing, setEditing] = useState(!pipeline.hasConnector)

  const selected = TYPES.find(t => t.value === type) || TYPES[0]

  const handleSave = async () => {
    setSaving(true); setMsg(null)
    try {
      await connectorApi.save(pipeline.id, { connectorType: type, connectionUrl: url, query })
      setMsg({ text: 'Connector saved! Click Test Connection to verify.', ok: true })
      setEditing(false)
      onUpdated()
    } catch(e) {
      setMsg({ text: e.response?.data?.detail || 'Failed to save', ok: false })
    } finally { setSaving(false) }
  }

  const handleTest = async () => {
    setTesting(true); setMsg(null); setPreview(null)
    try {
      const res = await connectorApi.test(pipeline.id)
      if (res.data.success) {
        setMsg({ text: res.data.message, ok: true })
        setPreview(res.data.preview)
      } else {
        setMsg({ text: res.data.message, ok: false })
      }
      onUpdated()
    } catch(e) {
      setMsg({ text: e.response?.data?.detail || 'Test failed', ok: false })
    } finally { setTesting(false) }
  }

  const handleRemove = async () => {
    if (!window.confirm('Remove connector? Pipeline will revert to CSV mode.')) return
    await connectorApi.remove(pipeline.id)
    setEditing(true); setPreview(null); setMsg(null); setUrl(''); setQuery('')
    onUpdated()
  }

  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
          <Database size={15} className="text-indigo-400"/> Data Source Connector
        </h2>
        {pipeline.hasConnector && (
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_STYLE[pipeline.connectorStatus]}`}>
              {pipeline.connectorStatus}
            </span>
            <button onClick={() => setEditing(e => !e)} className="text-xs text-indigo-400 hover:text-indigo-300">
              {editing ? 'Cancel' : 'Edit'}
            </button>
            <button onClick={handleRemove} className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1">
              <Trash2 size={11}/> Remove
            </button>
          </div>
        )}
      </div>

      {/* Current connector summary (not editing) */}
      {pipeline.hasConnector && !editing && (
        <div className="bg-gray-800/50 rounded-lg p-3 space-y-1">
          <p className="text-xs text-gray-400">Type: <span className="text-gray-200 font-medium">{pipeline.connectorType?.toUpperCase()}</span></p>
          {pipeline.query && <p className="text-xs text-gray-400">Query: <span className="font-mono text-indigo-300">{pipeline.query}</span></p>}
          {pipeline.lastError && <p className="text-xs text-red-400 mt-1">Last error: {pipeline.lastError}</p>}
          <div className="flex gap-2 pt-2">
            <button onClick={handleTest} disabled={testing} className="btn-primary flex items-center gap-1.5 text-xs px-3 py-1.5">
              <TestTube size={12}/>{testing ? 'Testing...' : 'Test Connection'}
            </button>
          </div>
        </div>
      )}

      {/* Connector form */}
      {editing && (
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-2">Connector type</label>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
              {TYPES.map(t => (
                <button key={t.value} onClick={() => setType(t.value)}
                  className={`p-3 rounded-lg border text-sm transition-colors text-center ${
                    type === t.value ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300' : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600'
                  }`}>
                  <span className="text-lg block mb-1">{t.icon}</span>
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1.5">
              {type === 'api' ? 'Base URL' : 'Connection string'}
            </label>
            <input className="input font-mono text-sm" value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder={selected.placeholder_url}/>
            <p className="text-xs text-gray-600 mt-1">
              {type === 'api' ? 'Base URL of the API (e.g. https://api.example.com)' : 'Include username, password, host, port, and database name'}
            </p>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1.5">
              {type === 'api' ? 'API endpoint path' : 'SQL query'}
            </label>
            <textarea className="input font-mono text-sm resize-none" rows={3}
              value={query} onChange={e => setQuery(e.target.value)}
              placeholder={selected.placeholder_q}/>
            <p className="text-xs text-gray-600 mt-1">
              {type === 'api' ? 'Endpoint path or full URL. Must return a JSON array.' : 'Only SELECT queries allowed. Add LIMIT to avoid fetching too many rows.'}
            </p>
          </div>

          <button onClick={handleSave} disabled={saving || !url || !query}
            className="btn-primary flex items-center gap-2">
            <Plug size={14}/>{saving ? 'Saving...' : 'Save Connector'}
          </button>
        </div>
      )}

      {/* Status message */}
      {msg && (
        <div className={`flex items-start gap-2 text-sm rounded-lg p-3 border ${msg.ok ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
          {msg.ok ? <CheckCircle size={15} className="flex-shrink-0 mt-0.5"/> : <XCircle size={15} className="flex-shrink-0 mt-0.5"/>}
          {msg.text}
        </div>
      )}

      {/* Data preview */}
      {preview && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-300">Data preview — {preview.rows} rows, {preview.columns.length} columns</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr>{preview.columns.slice(0,6).map(c => (
                  <th key={c} className="text-left text-gray-500 pb-1 pr-4 font-medium">{c}</th>
                ))}</tr>
              </thead>
              <tbody>
                {preview.sample.map((row, i) => (
                  <tr key={i} className="border-t border-gray-800">
                    {preview.columns.slice(0,6).map(c => (
                      <td key={c} className="py-1.5 pr-4 text-gray-300 font-mono">{String(row[c] ?? '').slice(0,20)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-green-400">✓ Connection verified. Click "Run Now" to analyze this data.</p>
        </div>
      )}

      {/* Info box when no connector */}
      {!pipeline.hasConnector && !editing && (
        <div className="bg-gray-800/30 rounded-lg p-4 text-center">
          <Database size={28} className="mx-auto mb-2 text-gray-600"/>
          <p className="text-sm text-gray-400">No connector configured</p>
          <p className="text-xs text-gray-600 mt-1">Pipeline currently uses CSV uploads. Add a connector to monitor live data.</p>
          <button onClick={() => setEditing(true)} className="btn-secondary mt-3 text-xs">Add Connector</button>
        </div>
      )}
    </div>
  )
}
