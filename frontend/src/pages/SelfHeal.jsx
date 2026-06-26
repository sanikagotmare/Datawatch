import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { healApi } from '../services/api'
import {
  Upload, CheckCircle, AlertTriangle, Download,
  Loader, FileText, Eye, History, X, Zap
} from 'lucide-react'

const STEP_ICONS = {
  'Remove duplicates':    '🔁',
  'Fix data types':       '🔧',
  'Fill missing values':  '🩹',
  'Flag outliers':        '⚠️',
}

const STATUS_COLOR = {
  fixed:   'text-green-400 bg-green-500/10 border-green-500/20',
  flagged: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
  ok:      'text-gray-400 bg-gray-800 border-gray-700',
}

export default function SelfHeal() {
  const [file,        setFile]        = useState(null)
  const [phase,       setPhase]       = useState('idle')   // idle|healing|done|error
  const [result,      setResult]      = useState(null)
  const [error,       setError]       = useState('')
  const [showPreview, setShowPreview] = useState(false)
  const [history,     setHistory]     = useState([])
  const [loadingHist, setLoadingHist] = useState(true)

  useEffect(() => {
    healApi.history().then(r => setHistory(r.data)).finally(() => setLoadingHist(false))
  }, [])

  const onDrop = useCallback(accepted => {
    if (accepted.length) { setFile(accepted[0]); setResult(null); setPhase('idle') }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'], 'application/json': ['.json'] },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024
  })

  const handleHeal = async () => {
    if (!file) return
    setPhase('healing'); setError('')
    try {
      const res = await healApi.healUpload(file)
      setResult(res.data)
      setPhase('done')
      // Refresh history
      healApi.history().then(r => setHistory(r.data))
    } catch (e) {
      setError(e.response?.data?.detail || 'Healing failed. Check backend logs.')
      setPhase('error')
    }
  }

  const handleDownload = () => {
    if (!result?.healing_id) return
    const url = healApi.downloadUrl(result.healing_id)
    const a   = document.createElement('a')
    a.href    = '/api' + url.replace('/api', '')
    a.download= result.filename ? `healed_${result.filename}` : 'healed_data.csv'
    // Use the token
    fetch(url.startsWith('/api') ? url : `/api${url}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    }).then(r => r.blob()).then(blob => {
      const burl = URL.createObjectURL(blob)
      const a2   = document.createElement('a')
      a2.href    = burl
      a2.download= result.filename ? `healed_${result.filename}` : 'healed_data.csv'
      a2.click()
      URL.revokeObjectURL(burl)
    })
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Zap size={24} className="text-indigo-400"/> Self-Healing Engine
        </h1>
        <p className="text-gray-400 mt-1">Upload a dataset → AI detects issues → auto-fix → download clean CSV</p>
      </div>

      {/* Flow indicator */}
      <div className="flex items-center gap-2 overflow-x-auto py-1">
        {['Upload Dataset','Detect Issues','Auto Heal','Healing Report','Download CSV'].map((s,i,arr) => (
          <div key={s} className="flex items-center gap-2 flex-shrink-0">
            <div className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-colors ${
              (phase==='done'&&i<=4)||(phase==='healing'&&i<=1)||(phase==='idle'&&i===0)
                ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                : 'bg-gray-800 border-gray-700 text-gray-500'
            }`}>{s}</div>
            {i < arr.length-1 && <span className="text-gray-700 flex-shrink-0">→</span>}
          </div>
        ))}
      </div>

      {/* Upload zone */}
      {phase === 'idle' && (
        <div className="space-y-4">
          <div {...getRootProps()} className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${isDragActive ? 'border-indigo-500 bg-indigo-500/5' : 'border-gray-700 hover:border-gray-600 hover:bg-gray-900'}`}>
            <input {...getInputProps()}/>
            <Upload size={36} className={`mx-auto mb-3 ${isDragActive ? 'text-indigo-400' : 'text-gray-600'}`}/>
            {isDragActive
              ? <p className="text-indigo-400 font-medium">Drop it here!</p>
              : <><p className="font-medium text-gray-200">Drag & drop your CSV or JSON here</p><p className="text-sm text-gray-500 mt-1">Max 50MB</p></>
            }
          </div>

          {file && (
            <div className="card p-4 flex items-center gap-3">
              <FileText size={20} className="text-indigo-400 flex-shrink-0"/>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm truncate">{file.name}</p>
                <p className="text-xs text-gray-500">{(file.size/1024).toFixed(1)} KB</p>
              </div>
              <button onClick={() => setFile(null)} className="text-gray-500 hover:text-red-400 text-xs">Remove</button>
            </div>
          )}

          <button onClick={handleHeal} disabled={!file}
            className="btn-primary w-full py-3 flex items-center justify-center gap-2 text-base">
            <Zap size={18}/> Auto Heal Dataset
          </button>
        </div>
      )}

      {/* Healing in progress */}
      {phase === 'healing' && (
        <div className="card text-center py-12">
          <Loader size={40} className="mx-auto mb-4 text-indigo-400 animate-spin"/>
          <h2 className="font-semibold text-lg mb-2">Healing {file?.name}...</h2>
          <div className="space-y-2 text-sm text-gray-500 mt-4">
            {['Removing duplicates','Fixing data types','Filling missing values','Flagging outliers'].map(s => (
              <p key={s} className="flex items-center justify-center gap-2"><Loader size={12} className="animate-spin text-indigo-500"/>{s}</p>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {phase === 'error' && (
        <div className="card text-center py-8">
          <AlertTriangle size={40} className="mx-auto mb-3 text-red-400"/>
          <h2 className="text-lg font-bold mb-2">Healing Failed</h2>
          <p className="text-red-400 text-sm mb-4">{error}</p>
          <button onClick={() => setPhase('idle')} className="btn-secondary">Try Again</button>
        </div>
      )}

      {/* Done — healing report */}
      {phase === 'done' && result && (
        <div className="space-y-4">
          {/* Summary banner */}
          <div className="card bg-green-500/5 border-green-500/20 p-5">
            <div className="flex items-center gap-3 mb-4">
              <CheckCircle size={24} className="text-green-400 flex-shrink-0"/>
              <div>
                <h2 className="font-semibold text-green-300">Healing Complete!</h2>
                <p className="text-sm text-gray-400 mt-0.5">{result.filename}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label:'Missing Filled',      val:result.missing_filled,      color:'text-blue-400',   icon:'🩹' },
                { label:'Duplicates Removed',  val:result.duplicates_removed,  color:'text-green-400',  icon:'🔁' },
                { label:'Types Fixed',         val:result.type_fixes,          color:'text-purple-400', icon:'🔧' },
                { label:'Outliers Flagged',    val:result.outliers_flagged,    color:'text-yellow-400', icon:'⚠️' },
              ].map(s => (
                <div key={s.label} className="bg-gray-800/60 rounded-lg p-3 text-center">
                  <p className="text-lg mb-1">{s.icon}</p>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.val}</p>
                  <p className="text-xs text-gray-500 mt-1">{s.label}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 flex items-center gap-3 text-sm text-gray-400">
              <span className="bg-gray-800 px-3 py-1 rounded-full">{result.original_rows} rows → <span className="text-green-400 font-medium">{result.final_rows} rows</span></span>
              {result.original_rows !== result.final_rows && <span className="text-red-400 text-xs">({result.original_rows - result.final_rows} removed)</span>}
            </div>
          </div>

          {/* Step-by-step report */}
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">Healing Steps</h3>
            <div className="space-y-2">
              {result.steps?.map((step, i) => (
                <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border text-sm ${STATUS_COLOR[step.status] || STATUS_COLOR.ok}`}>
                  <span className="text-base flex-shrink-0">{STEP_ICONS[step.step] || '✓'}</span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{step.step}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${step.status==='fixed'?'bg-green-500/20':step.status==='flagged'?'bg-yellow-500/20':'bg-gray-700'}`}>
                        {step.status}
                      </span>
                    </div>
                    <p className="text-xs mt-0.5 opacity-80">{step.detail}</p>
                  </div>
                  {step.impact > 0 && <span className="text-xs font-bold flex-shrink-0">{step.impact} fixed</span>}
                </div>
              ))}
            </div>
          </div>

          {/* Preview + Download */}
          <div className="flex gap-3">
            <button onClick={() => setShowPreview(true)} className="btn-secondary flex items-center gap-2 flex-1 justify-center">
              <Eye size={16}/> Preview Cleaned Data
            </button>
            <button onClick={handleDownload} className="btn-primary flex items-center gap-2 flex-1 justify-center">
              <Download size={16}/> Download Cleaned CSV
            </button>
          </div>

          <button onClick={() => { setFile(null); setResult(null); setPhase('idle') }}
            className="w-full text-sm text-gray-500 hover:text-gray-300 transition-colors py-2">
            ← Heal another file
          </button>
        </div>
      )}

      {/* Preview modal */}
      {showPreview && result?.preview && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 px-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-5xl max-h-[80vh] overflow-auto shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold">Cleaned Dataset Preview <span className="text-gray-500 text-sm ml-2">(first 10 rows)</span></h2>
              <button onClick={() => setShowPreview(false)} className="text-gray-500 hover:text-gray-300"><X size={20}/></button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-700">
                    {result.columns?.map(c => (
                      <th key={c} className={`text-left pb-2 pr-4 font-medium ${c === '_is_outlier' ? 'text-yellow-400' : 'text-gray-400'}`}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.preview?.map((row, i) => (
                    <tr key={i} className={`border-b border-gray-800/50 ${row._is_outlier ? 'bg-yellow-500/5' : ''}`}>
                      {result.columns?.map(c => (
                        <td key={c} className={`py-2 pr-4 font-mono ${c === '_is_outlier' ? 'text-yellow-400' : 'text-gray-300'}`}>
                          {String(row[c] ?? '').slice(0, 30)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {result.outliers_flagged > 0 && (
              <p className="text-xs text-yellow-400 mt-3">⚠ Yellow rows are flagged as outliers — review before using for analysis</p>
            )}
          </div>
        </div>
      )}

      {/* Healing History */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
          <History size={15}/> Healing History
        </h2>
        {loadingHist ? (
          <div className="flex justify-center py-6"><div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"/></div>
        ) : history.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-6">No healing runs yet</p>
        ) : (
          <div className="space-y-2">
            {history.map(h => (
              <div key={h.id} className="flex items-center gap-3 p-3 rounded-lg bg-gray-800/40">
                <CheckCircle size={14} className="text-green-400 flex-shrink-0"/>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{h.filename || `Healing #${h.id}`}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {h.originalRows} → {h.finalRows} rows ·
                    {h.missingFilled > 0 && ` ${h.missingFilled} nulls filled ·`}
                    {h.duplicatesRemoved > 0 && ` ${h.duplicatesRemoved} dupes removed ·`}
                    {h.outliersCount > 0 && ` ${h.outliersCount} outliers flagged`}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-xs text-gray-500">{new Date(h.createdAt).toLocaleDateString()}</p>
                  <button
                    onClick={() => {
                      fetch(`/api/heal/${h.id}/download`, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
                        .then(r => r.blob()).then(blob => {
                          const url = URL.createObjectURL(blob)
                          const a   = document.createElement('a')
                          a.href    = url; a.download = h.filename || `healed_${h.id}.csv`; a.click()
                          URL.revokeObjectURL(url)
                        })
                    }}
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 mt-1">
                    <Download size={11}/> Download
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
