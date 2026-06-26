import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { incidentApi } from '../services/api'
import { ArrowLeft, AlertTriangle, CheckCircle, Clock, Shield, Lightbulb, TrendingUp } from 'lucide-react'

const STS = {
  OPEN:          'bg-red-500/10 text-red-400 border-red-500/20',
  INVESTIGATING: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  RESOLVED:      'bg-green-500/10 text-green-400 border-green-500/20',
}
const SEV_C = { LOW:'#22c55e', MEDIUM:'#eab308', HIGH:'#ef4444', CRITICAL:'#dc2626' }

export default function IncidentDetail() {
  const { id } = useParams()
  const [incident, setIncident] = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [updating, setUpdating] = useState(false)

  const load = () => incidentApi.get(id).then(r => setIncident(r.data)).finally(() => setLoading(false))
  useEffect(() => { load() }, [id])

  const updateStatus = async (status) => {
    setUpdating(true)
    try { await incidentApi.update(id, { status }); load() } finally { setUpdating(false) }
  }

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"/></div>
  if (!incident) return null

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-start gap-3">
        <Link to="/incidents" className="text-gray-400 hover:text-gray-200 mt-1"><ArrowLeft size={20}/></Link>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold">{incident.title}</h1>
            <span className={`text-xs px-2.5 py-1 rounded-full font-medium border ${STS[incident.status]}`}>{incident.status}</span>
            <span className="text-xs px-2.5 py-1 rounded-full font-medium"
              style={{ background:`${SEV_C[incident.severity]}22`, color:SEV_C[incident.severity], border:`1px solid ${SEV_C[incident.severity]}44` }}>
              {incident.severity}
            </span>
          </div>
          <div className="flex gap-4 mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1"><Clock size={11}/>{new Date(incident.createdAt).toLocaleString()}</span>
            {incident.resolvedAt && <span className="flex items-center gap-1"><CheckCircle size={11} className="text-green-400"/> Resolved {new Date(incident.resolvedAt).toLocaleString()}</span>}
            {incident.pipelineName && <span>Pipeline: <Link to={`/pipelines/${incident.pipelineId}`} className="text-indigo-400">{incident.pipelineName}</Link></span>}
          </div>
        </div>
      </div>

      {incident.status !== 'RESOLVED' && (
        <div className="card p-4">
          <p className="text-sm text-gray-400 mb-3">Update status</p>
          <div className="flex gap-2">
            {['OPEN','INVESTIGATING','RESOLVED'].map(s => (
              <button key={s} onClick={() => updateStatus(s)} disabled={updating || incident.status === s}
                className={`px-4 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  incident.status === s ? `${STS[s]} cursor-default` : 'border-gray-700 text-gray-400 hover:border-gray-600 bg-gray-800'
                }`}>
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {incident.description && (
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2"><AlertTriangle size={14} className="text-yellow-400"/> Description</h2>
          <p className="text-sm text-gray-300 leading-relaxed">{incident.description}</p>
          {incident.affectedColumn && <p className="text-xs text-gray-500 mt-2">Affected column: <span className="text-indigo-400 font-mono">{incident.affectedColumn}</span></p>}
        </div>
      )}

      <div className="space-y-3">
        {incident.rootCause && (
          <div className="card border-l-2 border-l-red-500">
            <h2 className="text-sm font-semibold text-red-400 mb-2 flex items-center gap-2"><Shield size={14}/> Root Cause</h2>
            <p className="text-sm text-gray-300 leading-relaxed">{incident.rootCause}</p>
          </div>
        )}
        {incident.businessImpact && (
          <div className="card border-l-2 border-l-yellow-500">
            <h2 className="text-sm font-semibold text-yellow-400 mb-2 flex items-center gap-2"><TrendingUp size={14}/> Business Impact</h2>
            <p className="text-sm text-gray-300 leading-relaxed">{incident.businessImpact}</p>
          </div>
        )}
        {incident.suggestedResolution && (
          <div className="card border-l-2 border-l-green-500">
            <h2 className="text-sm font-semibold text-green-400 mb-2 flex items-center gap-2"><Lightbulb size={14}/> Suggested Resolution</h2>
            <p className="text-sm text-gray-300 leading-relaxed">{incident.suggestedResolution}</p>
          </div>
        )}
      </div>

      {incident.confidenceScore != null && (
        <div className="card p-4 flex items-center gap-4">
          <div className="flex-1">
            <p className="text-xs text-gray-500 mb-2">AI Confidence Score</p>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                <div className="h-full rounded-full" style={{
                  width: `${Math.round(incident.confidenceScore * 100)}%`,
                  background: incident.confidenceScore >= 0.8 ? '#22c55e' : incident.confidenceScore >= 0.5 ? '#eab308' : '#ef4444'
                }}/>
              </div>
              <span className="text-sm font-medium w-10 flex-shrink-0">{Math.round(incident.confidenceScore * 100)}%</span>
            </div>
          </div>
          {incident.datasetName && (
            <div className="text-right flex-shrink-0">
              <p className="text-xs text-gray-500">Dataset</p>
              <Link to={`/report/${incident.datasetId}`} className="text-sm text-indigo-400 hover:text-indigo-300">{incident.datasetName}</Link>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
