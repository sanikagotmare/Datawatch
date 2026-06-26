import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { datasourceApi } from '../services/api'
import {
  Database, Plus, TestTube, Trash2, Table,
  ChevronDown, ChevronRight, CheckCircle, XCircle,
  Loader, BarChart2, X, RefreshCw
} from 'lucide-react'

const STATUS_STYLE = {
  CONNECTED: 'text-green-400 bg-green-500/10 border-green-500/20',
  ERROR:     'text-red-400 bg-red-500/10 border-red-500/20',
  UNTESTED:  'text-gray-400 bg-gray-500/10 border-gray-500/20',
}

const DB_TYPES = [
  { value:'sqlite',     label:'SQLite',     icon:'📁', defaultPort: null,
    hint:'File path to your .db file' },
  { value:'postgresql', label:'PostgreSQL', icon:'🐘', defaultPort: 5432,
    hint:'pip install psycopg2-binary required' },
  { value:'mysql',      label:'MySQL',      icon:'🐬', defaultPort: 3306,
    hint:'pip install pymysql required' },
]

export default function DataSources() {
  const navigate = useNavigate()
  const [sources,     setSources]     = useState([])
  const [loading,     setLoading]     = useState(true)
  const [showForm,    setShowForm]    = useState(false)
  const [expanded,    setExpanded]    = useState(null)
  const [preview,     setPreview]     = useState(null)
  const [analyzing,   setAnalyzing]   = useState(null)  // "sourceId-tableName"
  const [analyzeResult, setAnalyzeResult] = useState(null)
  const [retesting,   setRetesting]   = useState(null)

  // Form state
  const [form, setForm] = useState({
    name:'', dbType:'sqlite', host:'localhost',
    port:'', databaseName:'', username:'', password:''
  })
  const [testing,    setTesting]    = useState(false)
  const [saving,     setSaving]     = useState(false)
  const [testResult, setTestResult] = useState(null)

  const load = () =>
    datasourceApi.list().then(r => setSources(r.data)).finally(() => setLoading(false))

  useEffect(() => { load() }, [])

  const selectedType = DB_TYPES.find(t => t.value === form.dbType) || DB_TYPES[0]

  const handleTypeChange = (val) => {
    const t = DB_TYPES.find(d => d.value === val)
    setForm(f => ({ ...f, dbType: val, port: t?.defaultPort || '' }))
    setTestResult(null)
  }

  const handleTest = async () => {
    setTesting(true); setTestResult(null)
    try {
      const r = await datasourceApi.test({
        dbType: form.dbType, host: form.host, port: form.port,
        databaseName: form.databaseName,
        username: form.username, password: form.password
      })
      setTestResult({ success: r.data.success, message: r.data.message, tables: r.data.tables })
    } catch(e) {
      setTestResult({ success: false, message: e.response?.data?.detail || 'Test failed' })
    } finally { setTesting(false) }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await datasourceApi.save({
        ...form,
        name: form.name || `${form.dbType}-${form.databaseName}`
      })
      setShowForm(false)
      resetForm()
      load()
    } catch(e) {
      setTestResult({ success: false, message: e.response?.data?.detail || 'Save failed' })
    } finally { setSaving(false) }
  }

  const resetForm = () => {
    setForm({ name:'', dbType:'sqlite', host:'localhost', port:'', databaseName:'', username:'', password:'' })
    setTestResult(null)
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this data source?')) return
    await datasourceApi.delete(id); load()
  }

  const handleRetest = async (id) => {
    setRetesting(id)
    try { await datasourceApi.retest(id); load() }
    finally { setRetesting(null) }
  }

  const handlePreview = async (sourceId, tableName) => {
    setPreview({ loading: true, sourceId, tableName })
    try {
      const r = await datasourceApi.previewTable(sourceId, tableName)
      setPreview({ ...r.data, sourceId, tableName, loading: false })
    } catch(e) {
      setPreview({ error: e.response?.data?.detail || 'Failed to load preview', loading: false })
    }
  }

  const handleAnalyze = async (sourceId, tableName) => {
    const key = `${sourceId}-${tableName}`
    setAnalyzing(key)
    setAnalyzeResult(null)
    try {
      const r = await datasourceApi.analyzeTable(sourceId, tableName)
      const { dataset_id, anomalies, severity, rows, columns } = r.data
      setAnalyzeResult({
        ok: true,
        message: `✓ Analysis complete — ${rows} rows, ${anomalies} anomalies, severity: ${severity}`,
        datasetId: dataset_id,
        tableName
      })
    } catch(e) {
      setAnalyzeResult({
        ok: false,
        message: e.response?.data?.detail || 'Analysis failed. Check backend logs.'
      })
    } finally { setAnalyzing(null) }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"/>
    </div>
  )

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Data Sources</h1>
          <p className="text-gray-400 mt-0.5">
            Connect to databases and run AI analysis directly on live tables
          </p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16}/> Add Connection
        </button>
      </div>

      {/* Analyze result banner */}
      {analyzeResult && (
        <div className={`p-4 rounded-xl border flex items-start gap-3 ${
          analyzeResult.ok
            ? 'bg-green-500/10 border-green-500/20 text-green-400'
            : 'bg-red-500/10 border-red-500/20 text-red-400'
        }`}>
          {analyzeResult.ok
            ? <CheckCircle size={18} className="flex-shrink-0 mt-0.5"/>
            : <XCircle    size={18} className="flex-shrink-0 mt-0.5"/>
          }
          <div className="flex-1">
            <p className="text-sm font-medium">{analyzeResult.message}</p>
            {analyzeResult.datasetId && (
              <button
                onClick={() => navigate(`/report/${analyzeResult.datasetId}`)}
                className="text-xs underline mt-1 hover:opacity-80">
                View Full AI Report →
              </button>
            )}
          </div>
          <button onClick={() => setAnalyzeResult(null)}
            className="opacity-60 hover:opacity-100 flex-shrink-0">
            <X size={16}/>
          </button>
        </div>
      )}

      {/* Add connection modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4 overflow-y-auto py-8">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-lg shadow-2xl my-auto">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-semibold text-lg">Add Database Connection</h2>
              <button onClick={() => { setShowForm(false); resetForm() }}
                className="text-gray-500 hover:text-gray-300">
                <X size={20}/>
              </button>
            </div>

            <div className="space-y-4">
              {/* DB Type */}
              <div>
                <label className="block text-xs text-gray-400 mb-2">Database type</label>
                <div className="grid grid-cols-3 gap-2">
                  {DB_TYPES.map(t => (
                    <button key={t.value} onClick={() => handleTypeChange(t.value)}
                      className={`p-3 rounded-lg border text-sm text-center transition-colors ${
                        form.dbType === t.value
                          ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                          : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600'
                      }`}>
                      <span className="text-xl block mb-1">{t.icon}</span>
                      {t.label}
                    </button>
                  ))}
                </div>
                {selectedType.hint && (
                  <p className="text-xs text-yellow-500/80 mt-1.5">⚠ {selectedType.hint}</p>
                )}
              </div>

              {/* Name */}
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Connection name</label>
                <input className="input" placeholder="e.g. My Sales Database"
                  value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}/>
              </div>

              {/* SQLite: just file path */}
              {form.dbType === 'sqlite' ? (
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">SQLite file path</label>
                  <input className="input font-mono text-sm"
                    placeholder="./mydata.db  or  C:/path/to/database.db"
                    value={form.databaseName}
                    onChange={e => setForm({ ...form, databaseName: e.target.value })}/>
                  <p className="text-xs text-gray-600 mt-1">
                    Use an absolute path or relative to the backend folder
                  </p>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="col-span-2">
                      <label className="block text-xs text-gray-400 mb-1.5">Host</label>
                      <input className="input" placeholder="localhost"
                        value={form.host} onChange={e => setForm({ ...form, host: e.target.value })}/>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1.5">Port</label>
                      <input className="input" type="number" value={form.port}
                        onChange={e => setForm({ ...form, port: e.target.value })}/>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1.5">Database name</label>
                    <input className="input" placeholder="my_database"
                      value={form.databaseName}
                      onChange={e => setForm({ ...form, databaseName: e.target.value })}/>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-400 mb-1.5">Username</label>
                      <input className="input" value={form.username}
                        onChange={e => setForm({ ...form, username: e.target.value })}/>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1.5">Password</label>
                      <input className="input" type="password" value={form.password}
                        onChange={e => setForm({ ...form, password: e.target.value })}/>
                    </div>
                  </div>
                </>
              )}

              {/* Test result */}
              {testResult && (
                <div className={`flex items-start gap-2 text-sm p-3 rounded-lg border ${
                  testResult.success
                    ? 'bg-green-500/10 text-green-400 border-green-500/20'
                    : 'bg-red-500/10 text-red-400 border-red-500/20'
                }`}>
                  {testResult.success
                    ? <CheckCircle size={15} className="flex-shrink-0 mt-0.5"/>
                    : <XCircle    size={15} className="flex-shrink-0 mt-0.5"/>
                  }
                  <div>
                    <p>{testResult.message}</p>
                    {testResult.tables?.length > 0 && (
                      <p className="text-xs mt-1 opacity-80">
                        Tables found: {testResult.tables.slice(0,6).join(', ')}
                        {testResult.tables.length > 6 ? ` +${testResult.tables.length - 6} more` : ''}
                      </p>
                    )}
                  </div>
                </div>
              )}

              <div className="flex gap-3 pt-1">
                <button onClick={handleTest}
                  disabled={testing || !form.databaseName}
                  className="btn-secondary flex items-center gap-2">
                  <TestTube size={14}/>
                  {testing ? 'Testing...' : 'Test Connection'}
                </button>
                <button onClick={handleSave}
                  disabled={saving || !form.databaseName}
                  className="btn-primary flex items-center gap-2 flex-1 justify-center">
                  {saving ? 'Saving...' : 'Save & Connect'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {sources.length === 0 ? (
        <div className="card text-center py-16">
          <Database size={40} className="mx-auto mb-3 text-gray-700"/>
          <p className="text-gray-400 font-medium">No data sources connected</p>
          <p className="text-gray-600 text-sm mt-1 mb-4">
            Connect to SQLite, PostgreSQL, or MySQL to run AI analysis on live tables
          </p>
          <button onClick={() => setShowForm(true)} className="btn-primary mx-auto">
            Add your first connection
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {sources.map(s => (
            <div key={s.id} className="card p-0 overflow-hidden">
              {/* Header row */}
              <div
                className="flex items-center gap-4 p-4 cursor-pointer hover:bg-gray-800/30 transition-colors"
                onClick={() => setExpanded(expanded === s.id ? null : s.id)}>
                <div className="w-10 h-10 bg-gray-800 rounded-lg flex items-center justify-center text-xl flex-shrink-0">
                  {DB_TYPES.find(t => t.value === s.dbType)?.icon || '🗄️'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-100">{s.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {s.dbType.toUpperCase()} ·{' '}
                    {s.databaseName || s.host} ·{' '}
                    {s.tables?.length || 0} table{s.tables?.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_STYLE[s.status] || STATUS_STYLE.UNTESTED}`}>
                    {s.status}
                  </span>
                  <button
                    onClick={e => { e.stopPropagation(); handleRetest(s.id) }}
                    disabled={retesting === s.id}
                    className="text-gray-500 hover:text-indigo-400 transition-colors p-1"
                    title="Re-test connection">
                    <RefreshCw size={15} className={retesting === s.id ? 'animate-spin' : ''}/>
                  </button>
                  <button
                    onClick={e => { e.stopPropagation(); handleDelete(s.id) }}
                    className="text-gray-500 hover:text-red-400 transition-colors p-1"
                    title="Delete">
                    <Trash2 size={15}/>
                  </button>
                  {expanded === s.id
                    ? <ChevronDown  size={16} className="text-gray-500"/>
                    : <ChevronRight size={16} className="text-gray-500"/>
                  }
                </div>
              </div>

              {/* Expanded: tables list */}
              {expanded === s.id && (
                <div className="border-t border-gray-800 p-4">
                  {s.lastError && (
                    <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg p-3 mb-3">
                      <strong>Last error:</strong> {s.lastError}
                    </div>
                  )}

                  {s.status !== 'CONNECTED' && (
                    <div className="bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-xs rounded-lg p-3 mb-3">
                      Connection not verified. Click the refresh icon to re-test.
                    </div>
                  )}

                  {!s.tables || s.tables.length === 0 ? (
                    <p className="text-gray-500 text-sm">
                      No tables discovered. Re-test the connection.
                    </p>
                  ) : (
                    <>
                      <p className="text-xs text-gray-500 mb-3 font-medium uppercase tracking-wider">
                        {s.tables.length} Table{s.tables.length !== 1 ? 's' : ''} Found
                      </p>
                      <div className="space-y-2">
                        {s.tables.map(t => {
                          const key = `${s.id}-${t.tableName}`
                          const isAnalyzing = analyzing === key
                          return (
                            <div key={t.tableName}
                              className="flex items-center gap-3 p-3 bg-gray-800/40 rounded-lg">
                              <Table size={14} className="text-indigo-400 flex-shrink-0"/>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium font-mono">{t.tableName}</p>
                                <p className="text-xs text-gray-500">
                                  {t.rowCount != null
                                    ? `${t.rowCount.toLocaleString()} rows`
                                    : '? rows'} ·{' '}
                                  {t.columnCount != null ? `${t.columnCount} cols` : '? cols'}
                                </p>
                              </div>
                              <div className="flex gap-2 flex-shrink-0">
                                <button
                                  onClick={() => handlePreview(s.id, t.tableName)}
                                  className="text-xs text-gray-400 hover:text-indigo-400 border border-gray-700 hover:border-indigo-500 px-2.5 py-1.5 rounded-lg transition-colors">
                                  Preview
                                </button>
                                <button
                                  onClick={() => handleAnalyze(s.id, t.tableName)}
                                  disabled={isAnalyzing || !!analyzing}
                                  className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-2.5 py-1.5 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-1.5">
                                  {isAnalyzing
                                    ? <><Loader size={11} className="animate-spin"/> Analyzing...</>
                                    : <><BarChart2 size={11}/> Analyze</>
                                  }
                                </button>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Preview modal */}
      {preview && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 px-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-4xl max-h-[80vh] overflow-auto shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold">
                Preview:{' '}
                <span className="font-mono text-indigo-300">{preview.tableName}</span>
              </h2>
              <button onClick={() => setPreview(null)} className="text-gray-500 hover:text-gray-300">
                <X size={20}/>
              </button>
            </div>

            {preview.loading ? (
              <div className="flex items-center justify-center h-32">
                <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"/>
              </div>
            ) : preview.error ? (
              <p className="text-red-400 text-sm">{preview.error}</p>
            ) : (
              <>
                <p className="text-xs text-gray-500 mb-3">
                  {preview.rows} rows · {preview.columns?.length} columns
                  (showing first 10 rows)
                </p>
                <div className="overflow-x-auto rounded-lg border border-gray-800">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-800/60">
                      <tr>
                        {preview.columns?.slice(0,8).map(c => (
                          <th key={c} className="text-left text-gray-400 px-3 py-2 font-medium whitespace-nowrap">
                            {c}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.sample?.map((row, i) => (
                        <tr key={i} className="border-t border-gray-800/50 hover:bg-gray-800/20">
                          {preview.columns?.slice(0,8).map(c => (
                            <td key={c} className="px-3 py-2 text-gray-300 font-mono whitespace-nowrap">
                              {String(row[c] ?? '').slice(0, 30) || (
                                <span className="text-gray-600 italic">null</span>
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="flex gap-3 mt-4">
                  <button
                    onClick={() => {
                      setPreview(null)
                      handleAnalyze(preview.sourceId, preview.tableName)
                    }}
                    className="btn-primary flex items-center gap-2 text-sm">
                    <BarChart2 size={14}/> Run AI Analysis on this Table
                  </button>
                  <button onClick={() => setPreview(null)} className="btn-secondary text-sm">
                    Close
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
