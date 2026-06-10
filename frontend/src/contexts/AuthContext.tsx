import React, { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
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
  signIn: () => Promise<void>
  signOut: () => Promise<void>
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
          email: (payload['email'] as string | undefined) ?? result.user.signInDetails?.loginId,
          given_name: payload['given_name'] as string | undefined,
          family_name: payload['family_name'] as string | undefined,
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

  const signIn = async () => {
    await AuthService.redirectToSignIn()
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

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    signIn,
    signOut,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
