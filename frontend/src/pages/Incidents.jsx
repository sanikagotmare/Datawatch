import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { incidentApi } from '../services/api'
import { AlertTriangle, ChevronRight, CheckCircle, Search } from 'lucide-react'

const SEV = { LOW:'badge-low', MEDIUM:'badge-medium', HIGH:'badge-high', CRITICAL:'badge-critical' }
const STS = {
  OPEN:          'bg-red-500/10 text-red-400 border border-red-500/20',
  INVESTIGATING: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20',
  RESOLVED:      'bg-green-500/10 text-green-400 border border-green-500/20',
}

export default function Incidents() {
  const [incidents, setIncidents] = useState([])
  const [loading,   setLoading]   = useState(true)
  const [filter,    setFilter]    = useState('ALL')
  const [search,    setSearch]    = useState('')

  useEffect(() => { incidentApi.list().then(r => setIncidents(r.data)).finally(() => setLoading(false)) }, [])

  const filtered = incidents
    .filter(i => filter === 'ALL' || i.status === filter)
    .filter(i => !search || i.title.toLowerCase().includes(search.toLowerCase()))

  const counts = {
    ALL:           incidents.length,
    OPEN:          incidents.filter(i => i.status === 'OPEN').length,
    INVESTIGATING: incidents.filter(i => i.status === 'INVESTIGATING').length,
    RESOLVED:      incidents.filter(i => i.status === 'RESOLVED').length,
  }

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"/></div>

  return (
    <div className="space-y-6 max-w-4xl">
      <div><h1 className="text-2xl font-bold">Incidents</h1><p className="text-gray-400 mt-0.5">Track and resolve data quality incidents</p></div>

      <div className="flex items-center gap-2 flex-wrap">
        {Object.entries(counts).map(([key, count]) => (
          <button key={key} onClick={() => setFilter(key)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors ${filter === key ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-gray-800 text-gray-400 border-gray-700 hover:border-gray-600'}`}>
            {key} <span className="ml-1 opacity-70">{count}</span>
          </button>
        ))}
        <div className="flex-1 max-w-xs flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 ml-auto">
          <Search size={14} className="text-gray-500"/>
          <input className="bg-transparent text-sm text-gray-300 placeholder-gray-600 outline-none flex-1"
            placeholder="Search incidents..." value={search} onChange={e => setSearch(e.target.value)}/>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="card text-center py-16">
          <CheckCircle size={40} className="mx-auto mb-3 text-green-600"/>
          <p className="text-gray-400 font-medium">
            {incidents.length === 0 ? 'No incidents yet — data quality looks good!' : 'No incidents match your filter'}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(i => (
            <Link key={i.id} to={`/incidents/${i.id}`} className="card flex items-center gap-4 p-4 hover:border-gray-700 transition-colors group">
              <AlertTriangle size={18} className={i.severity === 'CRITICAL' || i.severity === 'HIGH' ? 'text-red-400' : 'text-yellow-400'}/>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm">{i.title}</p>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                  {i.pipelineName && <span>Pipeline: {i.pipelineName}</span>}
                  {i.affectedColumn && <span>Col: <span className="text-indigo-400">{i.affectedColumn}</span></span>}
                  <span>{new Date(i.createdAt).toLocaleDateString()}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className={SEV[i.severity] || 'badge-unknown'}>{i.severity}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STS[i.status]}`}>{i.status}</span>
                <ChevronRight size={16} className="text-gray-600 group-hover:text-gray-400"/>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
