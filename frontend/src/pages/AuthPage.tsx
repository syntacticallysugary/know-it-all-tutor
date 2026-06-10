import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const AuthPage = () => {
  const { isAuthenticated, signIn } = useAuth()

  if (isAuthenticated) {
    return <Navigate to="/app/dashboard" replace />
  }

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
            New here? You can register from the sign-in page. Accounts are reviewed before access is granted.
          </p>
        </div>
      </div>
    </div>
  )
}

export default AuthPage