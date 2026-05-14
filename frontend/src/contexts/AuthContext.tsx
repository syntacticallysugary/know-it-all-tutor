import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { Hub } from 'aws-amplify/utils'
import { fetchAuthSession } from 'aws-amplify/auth'
import { AuthService } from '../services/auth'

export interface User {
  userId: string
  username: string
  email?: string
  given_name?: string
  family_name?: string
  isAdmin: boolean
}

export interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  signIn: (username: string, password: string) => Promise<{ success: boolean; error?: string }>
  signUp: (params: { username: string; password: string; email: string; given_name?: string; family_name?: string }) => Promise<{ success: boolean; error?: string; requiresConfirmation?: boolean }>
  signOut: () => Promise<void>
  confirmSignUp: (username: string, code: string) => Promise<{ success: boolean; error?: string }>
  resendConfirmationCode: (username: string) => Promise<{ success: boolean; error?: string }>
  resetPassword: (username: string) => Promise<{ success: boolean; error?: string }>
  confirmResetPassword: (username: string, code: string, newPassword: string) => Promise<{ success: boolean; error?: string }>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const checkAuthState = async () => {
    try {
      const result = await AuthService.getCurrentUser()
      if (result.success && result.user) {
        const session = await fetchAuthSession()
        const payload = session.tokens?.idToken?.payload ?? {}
        const groups: string[] = Array.isArray(payload['cognito:groups'])
          ? (payload['cognito:groups'] as string[])
          : []
        setUser({
          userId: result.user.userId,
          username: result.user.username,
          email: result.user.signInDetails?.loginId,
          isAdmin: groups.includes('admin'),
        })
      } else {
        setUser(null)
      }
    } catch (error) {
      console.error('Auth state check failed:', error)
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    checkAuthState()

    // Listen for auth events
    const unsubscribe = Hub.listen('auth', ({ payload }) => {
      switch (payload.event) {
        case 'signedIn':
          checkAuthState()
          break
        case 'signedOut':
          setUser(null)
          break
        case 'tokenRefresh':
          // Token refreshed successfully
          break
        case 'tokenRefresh_failure':
          // Token refresh failed, user needs to sign in again
          setUser(null)
          break
      }
    })

    return unsubscribe
  }, [])

  const signIn = async (username: string, password: string) => {
    setIsLoading(true)
    try {
      const result = await AuthService.signIn({ username, password })
      if (result.success) {
        await checkAuthState()
        return { success: true }
      } else {
        return { success: false, error: result.error }
      }
    } catch (error) {
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Sign in failed' 
      }
    } finally {
      setIsLoading(false)
    }
  }

  const signUp = async (params: { username: string; password: string; email: string; given_name?: string; family_name?: string }) => {
    setIsLoading(true)
    try {
      const result = await AuthService.signUp(params)
      if (result.success) {
        return { 
          success: true, 
          requiresConfirmation: !result.isSignUpComplete 
        }
      } else {
        return { success: false, error: result.error }
      }
    } catch (error) {
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Sign up failed' 
      }
    } finally {
      setIsLoading(false)
    }
  }

  const signOut = async () => {
    setIsLoading(true)
    try {
      await AuthService.signOut()
      setUser(null)
    } catch (error) {
      console.error('Sign out error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const confirmSignUp = async (username: string, code: string) => {
    setIsLoading(true)
    try {
      const result = await AuthService.confirmSignUp({ username, confirmationCode: code })
      if (result.success) {
        return { success: true }
      } else {
        return { success: false, error: result.error }
      }
    } catch (error) {
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Confirmation failed' 
      }
    } finally {
      setIsLoading(false)
    }
  }

  const resendConfirmationCode = async (username: string) => {
    try {
      const result = await AuthService.resendConfirmationCode(username)
      if (result.success) {
        return { success: true }
      } else {
        return { success: false, error: result.error }
      }
    } catch (error) {
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Resend failed' 
      }
    }
  }

  const resetPassword = async (username: string) => {
    try {
      const result = await AuthService.resetPassword({ username })
      if (result.success) {
        return { success: true }
      } else {
        return { success: false, error: result.error }
      }
    } catch (error) {
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Reset password failed' 
      }
    }
  }

  const confirmResetPassword = async (username: string, code: string, newPassword: string) => {
    try {
      const result = await AuthService.confirmResetPassword({ 
        username, 
        confirmationCode: code, 
        newPassword 
      })
      if (result.success) {
        return { success: true }
      } else {
        return { success: false, error: result.error }
      }
    } catch (error) {
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Password reset confirmation failed' 
      }
    }
  }

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    signIn,
    signUp,
    signOut,
    confirmSignUp,
    resendConfirmationCode,
    resetPassword,
    confirmResetPassword,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
