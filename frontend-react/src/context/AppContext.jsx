import { createContext, useContext, useState, useCallback, useRef } from 'react'

const AppContext = createContext(null)

export function AppProvider({ children }) {
  const [toast, setToast] = useState(null)
  const timerRef = useRef(null)

  const showToast = useCallback((message) => {
    if (timerRef.current) clearTimeout(timerRef.current)
    setToast(message)
    timerRef.current = setTimeout(() => setToast(null), 3000)
  }, [])

  return (
    <AppContext.Provider value={{ toast, showToast }}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
