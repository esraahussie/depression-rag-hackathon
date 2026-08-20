import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ChatPage from './pages/ChatPage'
import Phq9Page from './pages/Phq9Page'
import Gad7Page from './pages/Gad7Page'
import EpdsPage from './pages/EpdsPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/phq9" element={<Phq9Page />} />
        <Route path="/gad7" element={<Gad7Page />} />
        <Route path="/epds" element={<EpdsPage />} />
      </Routes>
    </Layout>
  )
}