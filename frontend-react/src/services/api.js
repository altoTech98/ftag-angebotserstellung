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

// V2 Upload
export const uploadSingleV2 = (file) => {
  const form = new FormData()
  form.append('file', file)
  return request('/v2/upload/single', { method: 'POST', body: form })
}

export const uploadFolderV2 = (files) => {
  const form = new FormData()
  for (const f of files) form.append('files', f)
  return request('/v2/upload', { method: 'POST', body: form })
}

// V2 Analysis
export const startV2Analysis = (tenderId) =>
  request('/v2/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tender_id: tenderId }),
  })

export function createV2SSE(jobId) {
  const token = getToken()
  const url = `${API_BASE}/v2/analyze/stream/${jobId}${token ? `?token=${encodeURIComponent(token)}` : ''}`
  return new EventSource(url)
}

export const getV2JobStatus = (jobId) =>
  request(`/v2/analyze/status/${jobId}`)

// V2 Offer Generation
export const generateV2Offer = (analysisId) =>
  request('/offer/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ analysis_id: analysisId }),
  })

export const getV2OfferStatus = (jobId) =>
  request(`/offer/status/${jobId}`)

export const downloadV2Result = async (resultId, filename) => {
  const token = getToken()
  const res = await fetch(`${API_BASE}/offer/${resultId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    throw new ApiError(
      res.status === 410
        ? 'Ergebnis abgelaufen – bitte erneut generieren.'
        : `Download fehlgeschlagen (HTTP ${res.status})`,
      res.status,
    )
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || `Machbarkeitsanalyse_${resultId}.xlsx`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

// V2 Feedback
export const saveV2Feedback = (body) =>
  request('/v2/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

// Job status (used by useSSE pollFallback)
export const getJobStatus = (jobId, statusPath = '/analyze/status/') =>
  request(`${statusPath}${jobId}`)

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

// Product search (used by CorrectionModal)
export const searchProducts = (query, limit = 15) =>
  request(`/products/search?q=${encodeURIComponent(query)}&limit=${limit}`)

// Health
export const checkHealth = async () => {
  const res = await fetch(`${API_BASE}/health`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export { ApiError }
