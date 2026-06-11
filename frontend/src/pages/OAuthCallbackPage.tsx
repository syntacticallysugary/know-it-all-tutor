import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

// Renders while Amplify exchanges the OAuth authorization code for tokens.
// The Hub 'signedIn' event in AuthContext populates the user; once that
// happens we redirect to the dashboard. Staying at /callback (rather than
// letting the wildcard route navigate away) is what lets Amplify read the
// ?code=...&state=... params before they are stripped from the URL.
const OAuthCallbackPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate('/app/dashboard', { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600 mx-auto mb-4" />
        <p className="text-gray-600 text-sm">Signing you in…</p>
      </div>
    </div>
  )
}

export default OAuthCallbackPage
