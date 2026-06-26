import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { dashboardApi } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import { Database, TrendingUp, AlertTriangle, Upload, GitBranch, CheckCircle, XCircle } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend } from 'recharts'

const SEV_C = { LOW:'#22c55e', MEDIUM:'#eab308', HIGH:'#ef4444', CRITICAL:'#dc2626' }

function StatCard({ icon: Icon, label, value, color='indigo', sub }) {
  const bg = { indigo:'bg-indigo-500/10 text-indigo-400', green:'bg-green-500/10 text-green-400', red:'bg-red-500/10 text-red-400', yellow:'bg-yellow-500/10 text-yellow-400', orange:'bg-orange-500/10 text-orange-400' }
  return (
    <div className="card flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${bg[color]}`}><Icon size={22}/></div>
      <div><p className="text-2xl font-bold">{value}</p><p className="text-sm text-gray-400">{label}</p>{sub&&<p className="text-xs text-gray-600 mt-0.5">{sub}</p>}</div>
    </div>
  )
}

const Tip = ({ active, payload, label }) => {
  if (!active||!payload?.length) return null
  return <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs"><p className="text-gray-300 mb-1">{label}</p>{payload.map((p,i)=><p key={i} style={{color:p.color}}>{p.name}: {p.value}</p>)}</div>
}

export default function Dashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(()=>{ dashboardApi.stats().then(r=>setStats(r.data)).finally(()=>setLoading(false)) },[])

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"/></div>
  if (!stats) return null

  const piData = [
    { name:'Healthy', value:Number(stats.healthyPipelines), color:'#22c55e' },
    { name:'Warning', value:Number(stats.warningPipelines), color:'#eab308' },
    { name:'Failed',  value:Number(stats.failedPipelines),  color:'#ef4444' },
  ].filter(d=>d.value>0)

  const barData = (stats.recentHistory||[]).slice(0,8).reverse().map((h,i)=>({ name:h.pipelineName?.slice(0,8)||`R${i+1}`, anomalies:h.anomaliesFound, result:h.result }))

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold">Dashboard</h1><p className="text-gray-400 mt-0.5">Welcome back, {user?.name}</p></div>
        <Link to="/upload" className="btn-primary flex items-center gap-2"><Upload size={16}/> Upload Dataset</Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard icon={GitBranch}     label="Total Pipelines"   value={stats.totalPipelines}           color="indigo"/>
        <StatCard icon={CheckCircle}   label="Healthy"           value={stats.healthyPipelines}         color="green"/>
        <StatCard icon={XCircle}       label="Failed"            value={stats.failedPipelines}          color="red"/>
        <StatCard icon={AlertTriangle} label="Open Incidents"    value={stats.openIncidents}            color="orange" sub={stats.criticalIncidents>0?`${stats.criticalIncidents} critical`:undefined}/>
        <StatCard icon={TrendingUp}    label="Anomalies (7d)"    value={stats.totalAnomaliesLast7Days}  color="yellow"/>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Pipeline Health Distribution</h2>
          {piData.length>0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={piData} cx="50%" cy="50%" innerRadius={50} outerRadius={75} dataKey="value" paddingAngle={3}>
                  {piData.map((e,i)=><Cell key={i} fill={e.color}/>)}
                </Pie>
                <Tooltip contentStyle={{background:'#111827',border:'1px solid #1f2937',borderRadius:8}}/>
                <Legend formatter={v=><span className="text-gray-400 text-xs">{v}</span>}/>
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-500 text-sm text-center py-12">No pipelines yet. <Link to="/pipelines" className="text-indigo-400">Create one →</Link></p>}
        </div>

        <div className="card">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Anomalies per Monitoring Run</h2>
          {barData.length>0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={barData} barSize={20}>
                <XAxis dataKey="name" tick={{fill:'#9ca3af',fontSize:10}} axisLine={false} tickLine={false}/>
                <YAxis tick={{fill:'#9ca3af',fontSize:10}} axisLine={false} tickLine={false}/>
                <Tooltip content={<Tip/>}/>
                <Bar dataKey="anomalies" radius={[4,4,0,0]}>
                  {barData.map((e,i)=><Cell key={i} fill={e.result==='FAILURE'?'#ef4444':e.anomalies>0?'#eab308':'#6366f1'}/>)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-500 text-sm text-center py-12">No monitoring runs yet</p>}
        </div>

        <div className="card flex flex-col items-center justify-center">
          <h2 className="text-sm font-semibold text-gray-300 mb-4 self-start">Avg Dataset Health</h2>
          <div className="relative w-28 h-28">
            <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
              <circle cx="50" cy="50" r="40" fill="none" stroke="#1f2937" strokeWidth="10"/>
              <circle cx="50" cy="50" r="40" fill="none"
                stroke={stats.avgHealthScore>=70?'#22c55e':stats.avgHealthScore>=40?'#eab308':'#ef4444'}
                strokeWidth="10" strokeDasharray={`${(stats.avgHealthScore/100)*251} 251`} strokeLinecap="round"/>
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-bold">{stats.avgHealthScore}%</span>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-3">{stats.totalDatasets} datasets · {stats.monitoringRunsLast7Days} runs (7d)</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <div className="flex items-center justify-between mb-4"><h2 className="text-sm font-semibold text-gray-300">Recent Incidents</h2><Link to="/incidents" className="text-xs text-indigo-400">View all →</Link></div>
          {(stats.recentIncidents||[]).length===0 ? <p className="text-gray-500 text-sm text-center py-8">No incidents yet</p>
          : (stats.recentIncidents||[]).map(i=>(
            <Link key={i.id} to={`/incidents/${i.id}`} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-gray-800 transition-colors">
              <AlertTriangle size={14} style={{color:SEV_C[i.severity]}} className="flex-shrink-0"/>
              <span className="text-sm text-gray-300 flex-1 truncate">{i.title}</span>
              <span className={`badge-${i.severity?.toLowerCase()}`}>{i.status}</span>
            </Link>
          ))}
        </div>
        <div className="card">
          <div className="flex items-center justify-between mb-4"><h2 className="text-sm font-semibold text-gray-300">Recent Datasets</h2><Link to="/upload" className="text-xs text-indigo-400">Upload →</Link></div>
          {(stats.recentDatasets||[]).length===0 ? <p className="text-gray-500 text-sm text-center py-8">No datasets yet</p>
          : (stats.recentDatasets||[]).map(d=>(
            <Link key={d.id} to={`/report/${d.id}`} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-gray-800 transition-colors">
              <Database size={14} className="text-indigo-400 flex-shrink-0"/>
              <span className="text-sm text-gray-300 flex-1 truncate">{d.filename}</span>
              <span className="text-sm font-medium mr-2">{d.healthScore}%</span>
              <span className={`badge-${d.severity}`}>{d.severity}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
