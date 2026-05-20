import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'

// Layout Components
import Layout from './components/Layout/Layout'
import ProtectedRoute from './components/Auth/ProtectedRoute'

// Page Components
import LandingPage from './pages/LandingPage'
import Dashboard from './pages/Dashboard'
import DomainLibrary from './pages/DomainLibrary'
import DomainDetails from './pages/DomainDetails'
import CreateDomain from './pages/CreateDomain'
import QuizInterface from './pages/QuizInterface'
import AdminPanel from './pages/AdminPanel'
import Profile from './pages/Profile'

// Auth Components
import AuthPage from './pages/AuthPage'

function App() {
  return (
    <AuthProvider>
      <div className="min-h-screen" style={{ backgroundColor: '#0B0F1A' }}>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth/*" element={<AuthPage />} />
          
          {/* Protected Routes */}
          <Route path="/app" element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }>
            <Route index element={<Navigate to="/app/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="domains" element={<DomainLibrary />} />
            <Route path="domains/create" element={<CreateDomain />} />
            <Route path="domains/detail/:subject" element={<DomainDetails />} />
            <Route path="domains/:domainId/edit" element={<CreateDomain />} />
            <Route path="quiz/:domainId" element={<QuizInterface />} />
            <Route path="profile" element={<Profile />} />
            <Route path="admin" element={<AdminPanel />} />
          </Route>
          
          {/* Catch all route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </AuthProvider>
  )
}

export default App