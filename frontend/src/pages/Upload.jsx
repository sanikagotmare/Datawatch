import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { datasetApi } from '../services/api'
import { Upload, FileText, CheckCircle, AlertCircle, Loader } from 'lucide-react'

const STEPS = [
  'Uploading file',
  'Running Isolation Forest ML detection',
  'Statistical Z-score analysis',
  'Generating data profiling charts',
  'PII & schema drift detection',
  'RAG memory retrieval (ChromaDB)',
  'Gemini LLM diagnosis + explainability',
  'Saving report'
]

export default function UploadPage() {
  const [file, setFile]       = useState(null)
  const [status, setStatus]   = useState('idle')
  const [step, setStep]       = useState(0)
  const [resultId, setResultId] = useState(null)
  const [error, setError]     = useState('')
  const navigate = useNavigate()

  const onDrop = useCallback(accepted => { if (accepted.length) setFile(accepted[0]) }, [])
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept:{'text/csv':['.csv'],'application/json':['.json']}, maxFiles:1, maxSize:50*1024*1024
  })

  const handleUpload = async () => {
    if (!file) return
    setStatus('uploading'); setError('')
    let s = 0
    const iv = setInterval(()=>{ s++; setStep(s); if(s>=STEPS.length-1) clearInterval(iv) }, 1600)
    try {
      const res = await datasetApi.upload(file)
      clearInterval(iv); setStep(STEPS.length); setResultId(res.data.id); setStatus('done')
    } catch(err) {
      clearInterval(iv)
      setError(err.response?.data?.detail || 'Upload failed. Is the backend running on port 8000?')
      setStatus('error')
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div><h1 className="text-2xl font-bold">Upload Dataset</h1><p className="text-gray-400 mt-1">Upload CSV or JSON → ML anomaly detection + AI analysis + data profiling charts</p></div>

      {status==='idle' && (
        <>
          <div {...getRootProps()} className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${isDragActive?'border-indigo-500 bg-indigo-500/5':'border-gray-700 hover:border-gray-600 hover:bg-gray-900'}`}>
            <input {...getInputProps()}/>
            <Upload size={40} className={`mx-auto mb-4 ${isDragActive?'text-indigo-400':'text-gray-600'}`}/>
            {isDragActive ? <p className="text-indigo-400 font-medium">Drop it here!</p> : (
              <><p className="font-medium text-gray-200">Drag & drop your file here</p><p className="text-sm text-gray-500 mt-1">CSV or JSON · max 50MB</p></>
            )}
          </div>
          {file && (
            <div className="card flex items-center gap-3 p-4">
              <FileText size={20} className="text-indigo-400 flex-shrink-0"/>
              <div className="flex-1 min-w-0"><p className="font-medium text-sm truncate">{file.name}</p><p className="text-xs text-gray-500">{(file.size/1024).toFixed(1)} KB</p></div>
              <button onClick={()=>setFile(null)} className="text-gray-500 hover:text-red-400 text-xs">Remove</button>
            </div>
          )}
          <button onClick={handleUpload} disabled={!file} className="btn-primary w-full py-3 text-base">Run AI Analysis</button>
        </>
      )}

      {status==='uploading' && (
        <div className="card space-y-4">
          <div className="flex items-center gap-3 mb-2"><Loader size={20} className="text-indigo-400 animate-spin"/><h2 className="font-semibold">Analyzing {file.name}...</h2></div>
          <div className="space-y-3">
            {STEPS.map((s,i)=>(
              <div key={i} className="flex items-center gap-3">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${i<step?'bg-green-500':i===step?'bg-indigo-500 animate-pulse':'bg-gray-700'}`}>
                  {i<step&&<CheckCircle size={12} className="text-white"/>}
                </div>
                <span className={`text-sm ${i<=step?'text-gray-200':'text-gray-600'}`}>{s}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {status==='done' && (
        <div className="card text-center py-8">
          <CheckCircle size={48} className="text-green-400 mx-auto mb-4"/>
          <h2 className="text-xl font-bold mb-2">Analysis Complete!</h2>
          <p className="text-gray-400 mb-6">ML anomaly detection, data profiling charts, and AI report are all ready.</p>
          <div className="flex gap-3 justify-center">
            <button onClick={()=>navigate(`/report/${resultId}`)} className="btn-primary">View Report</button>
            <button onClick={()=>{setFile(null);setStatus('idle');setStep(0)}} className="btn-secondary">Upload Another</button>
          </div>
        </div>
      )}

      {status==='error' && (
        <div className="card text-center py-8">
          <AlertCircle size={48} className="text-red-400 mx-auto mb-4"/>
          <h2 className="text-xl font-bold mb-2">Analysis Failed</h2>
          <p className="text-red-400 text-sm mb-6">{error}</p>
          <button onClick={()=>{setStatus('idle');setStep(0)}} className="btn-secondary">Try Again</button>
        </div>
      )}
    </div>
  )
}
