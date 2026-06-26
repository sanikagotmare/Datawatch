import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { datasetApi } from '../services/api'
import { ArrowLeft, CheckCircle, AlertTriangle, XCircle, Shield, Code, Brain, History, BarChart2, Zap, Download } from 'lucide-react'
import { healApi } from '../services/api'

const SevIcon = ({ s }) => s==='low'?<CheckCircle size={15} className="text-green-400"/>:s==='medium'?<AlertTriangle size={15} className="text-yellow-400"/>:<XCircle size={15} className="text-red-400"/>

function HealthGauge({ score }) {
  const c = score>=70?'#22c55e':score>=40?'#eab308':'#ef4444'
  return (
    <div className="relative w-28 h-28 flex-shrink-0">
      <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
        <circle cx="50" cy="50" r="40" fill="none" stroke="#1f2937" strokeWidth="10"/>
        <circle cx="50" cy="50" r="40" fill="none" stroke={c} strokeWidth="10"
          strokeDasharray={`${(score/100)*251} 251`} strokeLinecap="round"/>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold">{score}</span>
        <span className="text-xs text-gray-500">/100</span>
      </div>
    </div>
  )
}

export default function Report() {
  const { id } = useParams()
  const [report, setReport]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab]         = useState('overview')
  const [error, setError]     = useState('')
  const [healing,    setHealing]    = useState(false)
  const [healResult, setHealResult] = useState(null)
  const navigate = useNavigate()

  const handleHeal = async () => {
    setHealing(true); setHealResult(null)
    try {
      const res = await healApi.healDataset(id)
      setHealResult({ ok: true, data: res.data })
    } catch(e) {
      setHealResult({ ok: false, msg: e.response?.data?.detail || 'Healing failed' })
    } finally { setHealing(false) }
  }

  const handleDownloadHealed = (healingId) => {
    fetch(`/api/heal/${healingId}/download`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    }).then(r => r.blob()).then(blob => {
      const url = URL.createObjectURL(blob)
      const a   = document.createElement('a')
      a.href    = url
      a.download= `healed_${report?.filename || 'data.csv'}`
      a.click()
      URL.revokeObjectURL(url)
    })
  }

  useEffect(()=>{
    datasetApi.report(id).then(r=>setReport(r.data)).catch(e=>setError(e.response?.data?.detail||'Failed')).finally(()=>setLoading(false))
  },[id])

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"/></div>
  if (error)   return <div className="text-red-400 p-4">{error}</div>
  if (!report) return null

  const ai           = report.ai_report || {}
  const profile      = report.profile   || {}
  const charts       = profile.charts   || {}
  const quality      = profile.quality  || {}
  const anomalies    = report.anomalies || []
  const schemaDrift  = report.schema_issues || []
  const piiFields    = report.pii_fields    || []
  const pastFixes    = report.past_similar_fixes || []
  const issues       = ai.issues            || []
  const fixes        = ai.recommended_fixes || []
  const explainability = ai.explainability  || []

  const tabs = [
    { id:'overview', label:'Overview',                  icon:Brain },
    { id:'charts',   label:`Data Science (${Object.keys(charts).length} charts)`, icon:BarChart2 },
    { id:'issues',   label:`Issues (${issues.length})`, icon:AlertTriangle },
    { id:'fixes',    label:`Fixes (${fixes.length})`,   icon:Zap },
    { id:'explain',  label:`AI Explainability (${explainability.length})`, icon:Brain },
    { id:'pii',      label:`PII (${piiFields.length})`, icon:Shield },
    { id:'memory',   label:`RAG (${pastFixes.length})`, icon:History },
  ]

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center gap-3">
        <Link to="/dashboard" className="text-gray-400 hover:text-gray-200"><ArrowLeft size={20}/></Link>
        <div><h1 className="text-xl font-bold">{report.filename}</h1><p className="text-sm text-gray-500">{report.rows?.toLocaleString()} rows · {report.columns} columns</p></div>
      </div>

      {/* Summary */}
      <div className="card flex flex-col sm:flex-row gap-6 items-center sm:items-start">
        <HealthGauge score={ai.overall_data_health_score??0}/>
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h2 className="font-semibold">AI Summary</h2>
            <span className={`badge-${ai.severity||'low'}`}>{ai.severity||'unknown'}</span>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed">{ai.summary||'No summary available.'}</p>
          <div className="grid grid-cols-4 gap-3 mt-4">
            {[
              {label:'Anomalies',  val:anomalies.length,  color:'text-yellow-400'},
              {label:'Schema',     val:schemaDrift.length, color:'text-orange-400'},
              {label:'PII Fields', val:piiFields.length,  color:'text-red-400'},
              {label:'Fixes',      val:fixes.length,      color:'text-green-400'},
            ].map(s=>(
              <div key={s.label} className="bg-gray-800 rounded-lg p-3 text-center">
                <p className={`text-lg font-bold ${s.color}`}>{s.val}</p>
                <p className="text-xs text-gray-500">{s.label}</p>
              </div>
            ))}
          </div>
          {quality.overall && (
            <div className="grid grid-cols-3 gap-2 mt-3">
              {[
                {label:'Completeness', val:quality.completeness},
                {label:'Uniqueness',   val:quality.uniqueness},
                {label:'Validity',     val:quality.validity},
              ].map(q=>(
                <div key={q.label} className="text-center">
                  <p className="text-xs text-gray-500 mb-1">{q.label}</p>
                  <div className="h-1.5 bg-gray-700 rounded-full"><div className="h-full rounded-full bg-indigo-500" style={{width:`${q.val}%`}}/></div>
                  <p className="text-xs text-gray-400 mt-1">{q.val}%</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Self-Healing CTA */}
      <div className="card p-4 flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
            <Zap size={15} className="text-indigo-400"/> Auto-Heal This Dataset
          </h3>
          <p className="text-xs text-gray-500 mt-1">
            Fix missing values, remove duplicates, repair type issues, and flag outliers automatically.
          </p>
        </div>
        <button
          onClick={handleHeal}
          disabled={healing}
          className="btn-primary flex items-center gap-2 text-sm flex-shrink-0">
          <Zap size={14}/>
          {healing ? 'Healing...' : 'Auto Heal Dataset'}
        </button>
      </div>

      {/* Heal result */}
      {healResult && (
        <div className={`card p-4 space-y-3 ${healResult.ok ? 'border-green-500/30' : 'border-red-500/30'}`}>
          {healResult.ok ? (
            <>
              <div className="flex items-center gap-2">
                <CheckCircle size={16} className="text-green-400"/>
                <span className="text-sm font-medium text-green-400">Healing Complete!</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label:'Filled',    val: healResult.data.missing_filled,     color:'text-blue-400' },
                  { label:'Removed',   val: healResult.data.duplicates_removed,  color:'text-green-400' },
                  { label:'Type fixed',val: healResult.data.type_fixes,          color:'text-purple-400' },
                  { label:'Flagged',   val: healResult.data.outliers_flagged,    color:'text-yellow-400' },
                ].map(s => (
                  <div key={s.label} className="bg-gray-800 rounded-lg p-3 text-center">
                    <p className={`text-xl font-bold ${s.color}`}>{s.val}</p>
                    <p className="text-xs text-gray-500 mt-1">{s.label}</p>
                  </div>
                ))}
              </div>
              <div className="flex gap-2 pt-1">
                <button
                  onClick={() => handleDownloadHealed(healResult.data.healing_id)}
                  className="btn-primary flex items-center gap-2 text-sm">
                  <Download size={14}/> Download Cleaned CSV
                </button>
                <button
                  onClick={() => navigate('/heal')}
                  className="btn-secondary text-sm">
                  View Healing History
                </button>
              </div>
              {healResult.data.used_real_file === false && (
                <p className="text-xs text-yellow-500/80">
                  ⚠ Original file not found on disk — healing ran on reconstructed data.
                  Re-upload the file for real healing.
                </p>
              )}
            </>
          ) : (
            <div className="flex items-center gap-2 text-red-400 text-sm">
              <XCircle size={15}/> {healResult.msg}
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-800 flex gap-1 overflow-x-auto">
        {tabs.map(t=>(
          <button key={t.id} onClick={()=>setTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${tab===t.id?'border-indigo-500 text-indigo-400':'border-transparent text-gray-500 hover:text-gray-300'}`}>
            <t.icon size={12}/>{t.label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {tab==='overview' && (
        <div className="space-y-3">
          {anomalies.length===0&&schemaDrift.length===0&&<p className="text-gray-500 text-sm">No anomalies detected.</p>}
          {anomalies.map((a,i)=>(
            <div key={i} className="card p-4 flex items-start gap-3">
              <SevIcon s={a.severity}/>
              <div className="flex-1">
                <p className="text-sm font-medium">{a.type.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</p>
                <p className="text-xs text-gray-400 mt-0.5">Column: <span className="text-indigo-300">{a.column}</span> · {a.detail}</p>
                {a.detection_method&&<span className="text-xs bg-gray-800 text-gray-500 px-2 py-0.5 rounded mt-1 inline-block">{a.detection_method}</span>}
              </div>
              <span className={`badge-${a.severity} flex-shrink-0`}>{a.severity}</span>
            </div>
          ))}
          {schemaDrift.map((s,i)=>(
            <div key={i} className="card p-4 border-l-2 border-l-orange-500">
              <p className="text-sm font-medium text-orange-400">{s.type.replace(/_/g,' ')}</p>
              <p className="text-xs text-gray-400 mt-1">{s.detail}</p>
            </div>
          ))}
        </div>
      )}

      {/* Data Science Charts */}
      {tab==='charts' && (
        <div className="space-y-6">
          <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-xl p-4">
            <p className="text-sm font-medium text-indigo-400 mb-1">Data Science Profiling</p>
            <p className="text-xs text-gray-400">Charts generated server-side using matplotlib + seaborn in Python. Each chart is rendered as base64 PNG.</p>
          </div>
          {Object.entries(charts).map(([key, b64]) => (
            <div key={key} className="card p-4">
              <h3 className="text-sm font-medium text-gray-300 mb-3 capitalize">{key.replace(/_/g,' ')}</h3>
              <img src={`data:image/png;base64,${b64}`} alt={key} className="w-full rounded-lg"/>
            </div>
          ))}
          {Object.keys(charts).length===0&&<p className="text-gray-500 text-sm">No charts generated. Dataset may be too small.</p>}
        </div>
      )}

      {/* Issues */}
      {tab==='issues' && (
        <div className="space-y-3">
          {issues.length===0?<p className="text-gray-500 text-sm">No issues identified by AI.</p>:issues.map((issue,i)=>(
            <div key={i} className="card p-4 space-y-2">
              <div className="flex items-center gap-2"><h3 className="font-medium text-sm flex-1">{issue.title}</h3><span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">{issue.type}</span></div>
              <p className="text-sm text-gray-300">{issue.description}</p>
              {issue.impact&&<div className="bg-yellow-500/5 border border-yellow-500/20 rounded-lg p-3"><p className="text-xs text-yellow-400 font-medium mb-1">Business Impact</p><p className="text-xs text-gray-400">{issue.impact}</p></div>}
            </div>
          ))}
        </div>
      )}

      {/* Fixes */}
      {tab==='fixes' && (
        <div className="space-y-3">
          {fixes.length===0?<p className="text-gray-500 text-sm">No fixes generated.</p>:fixes.map((fix,i)=>(
            <div key={i} className="card p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-sm">{fix.issue}</h3>
                <div className="flex gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${fix.confidence>=0.8?'bg-green-500/20 text-green-400':'bg-yellow-500/20 text-yellow-400'}`}>{Math.round((fix.confidence||0)*100)}% conf</span>
                  {fix.auto_applicable&&<span className="text-xs bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-2 py-0.5 rounded-full">Auto</span>}
                </div>
              </div>
              <p className="text-sm text-gray-300">{fix.action}</p>
              {fix.python_code&&(
                <div className="bg-gray-950 rounded-lg p-3 border border-gray-700">
                  <div className="flex items-center gap-2 mb-2"><Code size={12} className="text-indigo-400"/><span className="text-xs text-gray-500">Python</span></div>
                  <code className="text-xs text-green-300 font-mono whitespace-pre-wrap">{fix.python_code}</code>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* AI Explainability */}
      {tab==='explain' && (
        <div className="space-y-4">
          <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-xl p-4">
            <p className="text-sm font-medium text-indigo-400 mb-1">AI Explainability Engine</p>
            <p className="text-xs text-gray-400">Root cause, business impact, and resolution steps generated by Gemini for each detected anomaly.</p>
          </div>
          {explainability.length===0?<p className="text-gray-500 text-sm">No explainability data yet.</p>:explainability.map((e,i)=>(
            <div key={i} className="space-y-2">
              <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Anomaly: {e.anomaly_type}</p>
              <div className="card p-4 border-l-2 border-l-red-500"><p className="text-xs text-red-400 font-medium mb-1">Root Cause</p><p className="text-sm text-gray-300">{e.root_cause}</p></div>
              <div className="card p-4 border-l-2 border-l-yellow-500"><p className="text-xs text-yellow-400 font-medium mb-1">Business Impact</p><p className="text-sm text-gray-300">{e.business_impact}</p></div>
              <div className="card p-4 border-l-2 border-l-green-500"><p className="text-xs text-green-400 font-medium mb-1">Suggested Resolution</p><p className="text-sm text-gray-300">{e.suggested_resolution}</p></div>
              <div className="flex items-center gap-3 px-1">
                <div className="flex-1 h-1.5 bg-gray-700 rounded-full"><div className="h-full rounded-full bg-indigo-500" style={{width:`${Math.round((e.confidence_score||0)*100)}%`}}/></div>
                <span className="text-xs text-gray-500">{Math.round((e.confidence_score||0)*100)}% confidence</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* PII */}
      {tab==='pii' && (
        <div className="space-y-4">
          {ai.pii_risk_summary&&<div className="bg-red-500/5 border border-red-500/20 rounded-xl p-4"><div className="flex items-center gap-2 mb-2"><Shield size={15} className="text-red-400"/><span className="text-sm font-medium text-red-400">AI PII Risk Assessment</span></div><p className="text-sm text-gray-300">{ai.pii_risk_summary}</p></div>}
          {piiFields.length===0?<p className="text-gray-500 text-sm">No PII detected.</p>:piiFields.map((p,i)=>(
            <div key={i} className="card p-4 flex items-center gap-3">
              <Shield size={18} className="text-red-400 flex-shrink-0"/>
              <div className="flex-1"><p className="text-sm font-medium">{p.column}</p><p className="text-xs text-gray-500 mt-0.5">Type: {p.pii_type} · via {p.detection_method}</p></div>
              <span className="badge-high">{p.risk} risk</span>
            </div>
          ))}
        </div>
      )}

      {/* RAG Memory */}
      {tab==='memory' && (
        <div className="space-y-4">
          <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-1"><History size={15} className="text-indigo-400"/><span className="text-sm font-medium text-indigo-400">RAG Memory — ChromaDB</span></div>
            <p className="text-xs text-gray-400">Past fixes retrieved semantically before calling the LLM. The similarity score shows how closely the past issue matches the current one.</p>
          </div>
          {pastFixes.length===0?<p className="text-gray-500 text-sm">No past fixes yet. Upload more datasets to build the knowledge base.</p>:pastFixes.map((pf,i)=>(
            <div key={i} className="card p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">Fix #{i+1} · Type: {pf.issue_type}</span>
                <div className="flex items-center gap-2">
                  <div className="w-20 h-1.5 bg-gray-700 rounded-full"><div className="h-full bg-indigo-500 rounded-full" style={{width:`${Math.round((pf.similarity_score||0)*100)}%`}}/></div>
                  <span className="text-xs text-indigo-400">{Math.round((pf.similarity_score||0)*100)}% similar</span>
                </div>
              </div>
              <p className="text-xs text-gray-400 font-mono bg-gray-800 rounded p-2">{pf.past_issue}</p>
              {pf.suggested_fixes?.slice(0,2).map((f,j)=><p key={j} className="text-xs text-green-400">✓ {f.action||JSON.stringify(f)}</p>)}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
