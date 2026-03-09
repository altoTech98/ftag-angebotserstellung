import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import LoginForm from './components/LoginForm'

function AppRoutes() {
  const { user, loading } = useAuth()

  if (loading) return null
  if (!user) return <LoginForm />

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/analyse" replace />} />
      <Route path="/analyse" element={<div>Analyse (TODO)</div>} />
      <Route path="/katalog" element={<div>Katalog (TODO)</div>} />
      <Route path="/historie" element={<div>Historie (TODO)</div>} />
      <Route path="/benutzer" element={
        user.role === 'admin' ? <div>Benutzer (TODO)</div> : <Navigate to="/analyse" replace />
      } />
      <Route path="*" element={<Navigate to="/analyse" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
