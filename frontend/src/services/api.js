import axios from 'axios'

const api = axios.create({
  baseURL: (import.meta.env.VITE_API_URL || "http://localhost:8000") + "/api"
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    return Promise.reject(err)
  }
)

export const authApi = {
  login:    (d) => api.post('/auth/login', d),
  register: (d) => api.post('/auth/register', d),
  me:       ()  => api.get('/auth/me'),
}

export const datasetApi = {
  upload: (file, pipelineId) => {
    const form = new FormData()
    form.append('file', file)
    if (pipelineId) form.append('pipeline_id', pipelineId)
    return api.post('/datasets/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  list:   ()   => api.get('/datasets'),
  report: (id) => api.get(`/datasets/${id}/report`),
}

export const dashboardApi = { stats: () => api.get('/dashboard') }

export const pipelineApi = {
  create:       (d)       => api.post('/pipelines', d),
  list:         ()        => api.get('/pipelines'),
  get:          (id)      => api.get(`/pipelines/${id}`),
  updateStatus: (id, s)   => api.patch(`/pipelines/${id}/status`, { status: s }),
  delete:       (id)      => api.delete(`/pipelines/${id}`),
  triggerRun:   (id)      => api.post(`/pipelines/${id}/run`),
  history:      (id)      => api.get(`/pipelines/${id}/history`),
}

export const incidentApi = {
  create: (d)      => api.post('/incidents', d),
  list:   ()       => api.get('/incidents'),
  get:    (id)     => api.get(`/incidents/${id}`),
  update: (id, d)  => api.patch(`/incidents/${id}`, d),
}

export default api

// Connector API
export const connectorApi = {
  save:   (pipelineId, data) => api.post(`/pipelines/${pipelineId}/connector`, data),
  test:   (pipelineId)       => api.post(`/pipelines/${pipelineId}/connector/test`),
  remove: (pipelineId)       => api.delete(`/pipelines/${pipelineId}/connector`),
}

// Feature 1: Data Sources
export const datasourceApi = {
  test:         (data)              => api.post('/datasources/test', data),
  save:         (data)              => api.post('/datasources', data),
  list:         ()                  => api.get('/datasources'),
  get:          (id)                => api.get(`/datasources/${id}`),
  retest:       (id)                => api.post(`/datasources/${id}/test`),
  delete:       (id)                => api.delete(`/datasources/${id}`),
  previewTable: (id, table)         => api.get(`/datasources/${id}/tables/${table}/preview`),
  analyzeTable: (id, table)         => api.post(`/datasources/${id}/tables/${table}/analyze`),
}

// Feature 2+3: Self-Healing
export const healApi = {
  healDataset:  (datasetId)         => api.post(`/heal/dataset/${datasetId}`),
  healUpload:   (file)              => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/heal/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  history:      ()                  => api.get('/heal/history'),
  preview:      (healingId)         => api.get(`/heal/${healingId}/preview`),
  downloadUrl:  (healingId)         => `/api/heal/${healingId}/download`,
}
