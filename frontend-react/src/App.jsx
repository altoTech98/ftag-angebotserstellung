import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import { AppProvider } from './context/AppContext'
import LoginForm from './components/LoginForm'
import Header from './components/Header'
import Toast from './components/Toast'
import AnalysePage from './pages/AnalysePage'

function AppRoutes() {
  const { user, loading } = useAuth()

  if (loading) return null
  if (!user) return <LoginForm />

  return (
    <>
      <Header />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Navigate to="/analyse" replace />} />
          <Route path="/analyse" element={<AnalysePage />} />
          <Route path="/katalog" element={<div>Katalog (TODO)</div>} />
          <Route path="/historie" element={<div>Historie (TODO)</div>} />
          <Route path="/benutzer" element={
            user.role === 'admin' ? <div>Benutzer (TODO)</div> : <Navigate to="/analyse" replace />
          } />
          <Route path="*" element={<Navigate to="/analyse" replace />} />
        </Routes>
      </main>
      <Toast />
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <AppRoutes />
      </AppProvider>
    </BrowserRouter>
  )
}
