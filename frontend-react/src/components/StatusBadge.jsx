import { useState, useEffect } from 'react'
import * as api from '../services/api'

export default function StatusBadge() {
  const [server, setServer] = useState({ online: false, text: 'Server' })
  const [ai, setAi] = useState({ online: false, text: 'KI' })

  useEffect(() => {
    const check = async () => {
      try {
        const data = await api.checkHealth()
        setServer({ online: true, text: 'Server' })
        if (data.ai?.engine === 'claude') {
          setAi({ online: true, text: 'Claude AI' })
        } else if (data.ai?.engine === 'ollama') {
          setAi({ online: true, text: 'Ollama' })
        } else if (data.ai?.engine === 'regex') {
          setAi({ online: true, text: 'Basis-Modus', warn: true })
        } else {
          setAi({ online: true, text: 'KI' })
        }
      } catch {
        setServer({ online: false, text: 'Offline' })
        setAi({ online: false, text: 'KI' })
      }
    }
    check()
    const interval = setInterval(check, 15000)
    return () => clearInterval(interval)
  }, [])

  const dotStyle = (online, warn) => ({
    width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
    background: online ? (warn ? '#d97706' : '#16a34a') : '#dc2626',
  })

  return (
    <>
      <div className="status-badge" title="Server-Status">
        <span style={dotStyle(server.online)} />
        <span>{server.text}</span>
      </div>
      <div className="status-badge" title="KI-Engine">
        <span style={dotStyle(ai.online, ai.warn)} />
        <span>{ai.text}</span>
      </div>
    </>
  )
}
