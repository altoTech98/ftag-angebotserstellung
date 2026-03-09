import { useRef, useCallback } from 'react'
import * as api from '../services/api'

export function useSSE() {
  const esRef = useRef(null)

  const pollSSE = useCallback((jobId, onProgress) => {
    return new Promise((resolve, reject) => {
      const es = api.createSSE(jobId)
      esRef.current = es
      let settled = false
      const settle = (fn, val) => {
        if (!settled) { settled = true; es.close(); fn(val) }
      }
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          if (data.type === 'keepalive') return
          if (data.progress && onProgress) onProgress(data.progress)
          if (data.status === 'completed') settle(resolve, data.result)
          if (data.status === 'failed') settle(reject, new Error(data.error || 'Analyse fehlgeschlagen'))
        } catch (err) {
          console.warn('SSE parse error:', err)
        }
      }
      es.onerror = () => settle(reject, new Error('SSE connection error'))
    })
  }, [])

  const pollFallback = useCallback(async (jobId, onProgress, statusPath = '/analyze/status/') => {
    const POLL_INTERVAL = 2000
    const MAX_POLLS = 450
    for (let i = 0; i < MAX_POLLS; i++) {
      await new Promise(r => setTimeout(r, POLL_INTERVAL))
      const job = await api.getJobStatus(jobId, statusPath)
      if (job.progress && onProgress) onProgress(job.progress)
      if (job.status === 'completed') return job.result
      if (job.status === 'failed') throw new Error(job.error || 'Verarbeitung fehlgeschlagen')
    }
    throw new Error('Timeout: Bitte erneut versuchen.')
  }, [])

  const pollJob = useCallback(async (jobId, onProgress, statusPath = '/analyze/status/') => {
    if (statusPath === '/analyze/status/') {
      try {
        return await pollSSE(jobId, onProgress)
      } catch (e) {
        console.warn('SSE fallback to polling:', e.message)
      }
    }
    return await pollFallback(jobId, onProgress, statusPath)
  }, [pollSSE, pollFallback])

  const cleanup = useCallback(() => {
    if (esRef.current) { esRef.current.close(); esRef.current = null }
  }, [])

  return { pollJob, cleanup }
}
