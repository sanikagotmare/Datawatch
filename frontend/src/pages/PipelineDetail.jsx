import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { pipelineApi } from '../services/api'
import { ArrowLeft, Play, CheckCircle, AlertTriangle, XCircle, Clock } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

const R_COLOR = { SUCCESS:'text-green-400', WARNING:'text-yellow-400', FAILURE:'text-red-400' }
const RIcon = ({ r }) => r==='SUCCESS' ? <CheckCircle size={14} className="text-green-400"/> : r==='WARNING' ? <AlertTriangle size={14} className="text-yellow-400"/> : <XCircle size={14} className="text-red-400"/>

export default function PipelineDetail() {
  const { id } = useParams()
  const [pipeline, setPipeline] = useState(null)
  const [history,  setHistory]  = useState([])
  const [running,  setRunning]  = useState(false)
  const [loading,  setLoading]  = useState(true)

  const load = async () => {
    const [pRes, hRes] = await Promise.all([pipelineApi.get(id), pipelineApi.history(id)])
    setPipeline(pRes.data); setHistory(hRes.data); setLoading(false)
  }
  useEffect(() => { load() }, [id])

  const triggerRun = async () => {
    setRunning(true)
    try { await pipelineApi.triggerRun(id); load() } finally { setRunning(false) }
  }

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"/></div>
  if (!pipeline) return null

  const sc = pipeline.status==='HEALTHY' ? 'text-green-400' : pipeline.status==='WARNING' ? 'text-yellow-400' : 'text-red-400'
  const sb = pipeline.status==='HEALTHY' ? 'bg-green-500/10' : pipeline.status==='WARNING' ? 'bg-yellow-500/10' : 'bg-red-500/10'
  const chartData = [...history].reverse().slice(-10).map((h, i) => ({ run: i+1, anomalies: h.anomaliesFound }))

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center gap-3">
        <Link to="/pipelines" className="text-gray-400 hover:text-gray-200"><ArrowLeft size={20}/></Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold">{pipeline.name}</h1>
            <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${sb} ${sc}`}>{pipeline.status}</span>
          </div>
          {pipeline.description && <p className="text-sm text-gray-500 mt-0.5">{pipeline.description}</p>}
        </div>
        <button onClick={triggerRun} disabled={running} className="btn-primary flex items-center gap-2">
          <Play size={15}/>{running ? 'Running...' : 'Run Now'}
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label:'Health Score',    value:`${pipeline.healthScore}%`,       color:sc },
          { label:'Successful Runs', value:pipeline.successfulRuns,           color:'text-green-400' },
          { label:'Failed Runs',     value:pipeline.failedRuns,               color:'text-red-400' },
          { label:'Open Incidents',  value:pipeline.openIncidents?.length||0, color:'text-yellow-400' },
        ].map(s => (
          <div key={s.label} className="card text-center">
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-xs text-gray-500 mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {chartData.length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Anomaly Trend</h2>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={chartData}>
              <XAxis dataKey="run" tick={{ fill:'#9ca3af', fontSize:11 }} axisLine={false} tickLine={false}/>
              <YAxis tick={{ fill:'#9ca3af', fontSize:11 }} axisLine={false} tickLine={false}/>
              <Tooltip contentStyle={{ background:'#111827', border:'1px solid #1f2937', borderRadius:8 }}/>
              <Line type="monotone" dataKey="anomalies" stroke="#6366f1" strokeWidth={2} dot={{ fill:'#6366f1', r:4 }}/>
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {pipeline.openIncidents?.length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Open Incidents</h2>
          <div className="space-y-2">
            {pipeline.openIncidents.map(i => (
              <Link key={i.id} to={`/incidents/${i.id}`} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-gray-800 transition-colors">
                <AlertTriangle size={14} className="text-red-400 flex-shrink-0"/>
                <span className="text-sm flex-1">{i.title}</span>
                <span className={`badge-${i.severity?.toLowerCase()}`}>{i.severity}</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Monitoring History</h2>
        {history.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-8">No runs yet. Click "Run Now" to trigger a check.</p>
        ) : (
          <div className="space-y-2">
            {history.map(h => (
              <div key={h.id} className="flex items-center gap-3 p-3 rounded-lg bg-gray-800/50">
                <RIcon r={h.result}/>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-medium ${R_COLOR[h.result]}`}>{h.result}</span>
                    {h.anomaliesFound > 0 && (
                      <span className="text-xs bg-yellow-500/10 text-yellow-400 px-2 py-0.5 rounded-full">{h.anomaliesFound} anomalies</span>
                    )}
                  </div>
                  {h.details && <p className="text-xs text-gray-500 truncate mt-0.5">{h.details}</p>}
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="flex items-center gap-1 text-xs text-gray-500"><Clock size={11}/>{h.durationMs}ms</div>
                  <p className="text-xs text-gray-600">{new Date(h.executionTime).toLocaleString()}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
