import React, { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import SignInForm from '../components/Auth/SignInForm'
import SignUpForm from '../components/Auth/SignUpForm'
import ConfirmSignUpForm from '../components/Auth/ConfirmSignUpForm'
import ForgotPasswordForm from '../components/Auth/ForgotPasswordForm'

type AuthView = 'signIn' | 'signUp' | 'confirmSignUp' | 'forgotPassword'

const AuthPage = () => {
  const { isAuthenticated } = useAuth()
  const [currentView, setCurrentView] = useState<AuthView>('signIn')
  const [pendingUsername, setPendingUsername] = useState('')

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/app/dashboard" replace />
  }

  const handleSignUpSuccess = (username: string) => {
    setPendingUsername(username)
    setCurrentView('confirmSignUp')
  }

  const handleConfirmationSuccess = () => {
    setCurrentView('signIn')
    setPendingUsername('')
  }

  const handleResetSuccess = () => {
    setCurrentView('signIn')
  }

  const renderCurrentView = () => {
    switch (currentView) {
      case 'signIn':
        return (
          <SignInForm
            onSwitchToSignUp={() => setCurrentView('signUp')}
            onSwitchToForgotPassword={() => setCurrentView('forgotPassword')}
          />
        )
      case 'signUp':
        return (
          <SignUpForm
            onSwitchToSignIn={() => setCurrentView('signIn')}
            onSignUpSuccess={handleSignUpSuccess}
          />
        )
      case 'confirmSignUp':
        return (
          <ConfirmSignUpForm
            username={pendingUsername}
            onConfirmationSuccess={handleConfirmationSuccess}
            onBackToSignUp={() => setCurrentView('signUp')}
          />
        )
      case 'forgotPassword':
        return (
          <ForgotPasswordForm
            onBackToSignIn={() => setCurrentView('signIn')}
            onResetSuccess={handleResetSuccess}
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="text-3xl font-bold text-primary-600 mb-8">
            Know-It-All Tutor
          </div>
        </div>
        
        <div className="bg-white p-8 rounded-lg shadow-md border">
          {renderCurrentView()}
        </div>
      </div>
    </div>
  )
}

export default AuthPage