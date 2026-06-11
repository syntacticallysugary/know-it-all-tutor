import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const AUTH_DOMAIN = `https://${import.meta.env.VITE_AUTH_DOMAIN || 'auth.syntacticallysugary.dev'}`
const CLIENT_ID = import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID || ''
const REDIRECT_URI = import.meta.env.VITE_REDIRECT_SIGN_IN || 'https://tutor.syntacticallysugary.dev/callback'
const OAUTH_PARAMS = `client_id=${CLIENT_ID}&response_type=code&scope=openid%20email%20profile&redirect_uri=${encodeURIComponent(REDIRECT_URI)}`

const AuthPage = () => {
  const { isAuthenticated, signIn } = useAuth()

  if (isAuthenticated) {
    return <Navigate to="/app/dashboard" replace />
  }

  const signUpUrl = `${AUTH_DOMAIN}/signup?${OAUTH_PARAMS}`
  const forgotPasswordUrl = `${AUTH_DOMAIN}/forgotPassword?${OAUTH_PARAMS}`

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="text-3xl font-bold text-primary-600 mb-8">
            Know-It-All Tutor
          </div>
          <p className="text-gray-600 mb-8">Sign in to access your knowledge domains.</p>
        </div>

        <div className="bg-white p-8 rounded-lg shadow-md border text-center">
          <button
            onClick={signIn}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            Sign In
          </button>
          <p className="mt-4 text-sm text-gray-500">
            <a href={signUpUrl} className="text-primary-600 hover:text-primary-500 font-medium">Request access</a>
            {' '}— accounts are reviewed before approval.
          </p>
          <p className="mt-2 text-sm text-gray-500">
            <a href={forgotPasswordUrl} className="text-primary-600 hover:text-primary-500">Forgot your password?</a>
          </p>
        </div>
      </div>
    </div>
  )
}

export default AuthPage