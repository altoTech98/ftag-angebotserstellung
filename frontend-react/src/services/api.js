const API_BASE = '/api'

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

function getToken() {
  return localStorage.getItem('auth_token')
}

async function request(path, opts = {}) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  const token = getToken()
  if (token) {
    opts.headers = opts.headers || {}
    opts.headers['Authorization'] = `Bearer ${token}`
  }

  let res
  try {
    res = await fetch(url, opts)
  } catch {
    throw new ApiError('Server nicht erreichbar. Ist der Server gestartet?', 0)
  }

  if (res.status === 401) {
    localStorage.removeItem('auth_token')
    window.dispatchEvent(new Event('auth:logout'))
    throw new ApiError('Sitzung abgelaufen – bitte erneut anmelden.', 401)
  }

  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const body = await res.json()
      msg = body.detail || body.message || msg
    } catch {}
    if (res.status === 410) {
      msg = msg || 'Datei abgelaufen – bitte erneut hochladen.'
    }
    throw new ApiError(msg, res.status)
  }

  try {
    return await res.json()
  } catch {
    throw new ApiError('Ungueltige Server-Antwort', 0)
  }
}

// Auth
export const login = (email, password) =>
  request('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })

export const getMe = () => request('/auth/me')

export const getUsers = () => request('/auth/users')

export const createUser = (email, password, role) =>
  request('/auth/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, role }),
  })

export const deleteUser = (email) =>
  request(`/auth/users/${encodeURIComponent(email)}`, { method: 'DELETE' })

// Upload
export const uploadFile = (file) => {
  const form = new FormData()
  form.append('file', file)
  return request('/upload', { method: 'POST', body: form })
}

export const uploadFolder = (files) => {
  const form = new FormData()
  for (const f of files) form.append('files', f)
  return request('/upload/folder', { method: 'POST', body: form })
}

// Analysis
export const startAnalysis = (fileId) =>
  request('/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: fileId }),
  })

export const startProjectAnalysis = (projectId) =>
  request('/analyze/project', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, file_overrides: {} }),
  })

export const getJobStatus = (jobId, statusPath = '/analyze/status/') =>
  request(`${statusPath}${jobId}`)

export function createSSE(jobId) {
  return new EventSource(`${API_BASE}/analyze/stream/${jobId}`)
}

// Result generation
export const generateResult = (requirements, matching) =>
  request('/result/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ requirements, matching }),
  })

export const getResultStatus = (jobId) =>
  request(`/result/status/${jobId}`)

export const getResultDownloadUrl = (resultId) =>
  `${API_BASE}/result/${resultId}/download`

// Catalog
export const getCatalogInfo = () => request('/catalog/info')

export const uploadCatalog = (file) => {
  const form = new FormData()
  form.append('file', file)
  return request('/catalog/upload', { method: 'POST', body: form })
}

// History
export const getHistory = () => request('/history')
export const getHistoryDetail = (id) => request(`/history/${id}`)
export const rematchHistory = (id) => request(`/history/${id}/rematch`, { method: 'POST' })
export const deleteHistory = (id) => request(`/history/${id}`, { method: 'DELETE' })

// Feedback
export const saveFeedback = (body) =>
  request('/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

export const searchProducts = (query, limit = 15) =>
  request(`/products/search?q=${encodeURIComponent(query)}&limit=${limit}`)

// Health
export const checkHealth = async () => {
  const res = await fetch('/health')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export { ApiError }
