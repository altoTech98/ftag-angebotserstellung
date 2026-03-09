import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/analyse" replace />} />
        <Route path="/analyse" element={<div>Analyse</div>} />
        <Route path="/katalog" element={<div>Katalog</div>} />
        <Route path="/historie" element={<div>Historie</div>} />
        <Route path="/benutzer" element={<div>Benutzer</div>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
