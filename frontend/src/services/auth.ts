import { signUp, signIn, signInWithRedirect, signOut, confirmSignUp, resendSignUpCode, resetPassword, confirmResetPassword, getCurrentUser, fetchAuthSession } from 'aws-amplify/auth'

export interface SignUpParams {
  username: string
  password: string
  email: string
  given_name?: string
  family_name?: string
}

export interface SignInParams {
  username: string
  password: string
}

export interface ConfirmSignUpParams {
  username: string
  confirmationCode: string
}

export interface ResetPasswordParams {
  username: string
}

export interface ConfirmResetPasswordParams {
  username: string
  confirmationCode: string
  newPassword: string
}

export interface AuthHeaders {
  'Content-Type': string
  'Authorization'?: string
}

export class AuthService {
  /**
   * Get authentication headers for API calls
   * Retrieves current Cognito session token and formats for Authorization header
   */
  static async getAuthHeaders(): Promise<AuthHeaders> {
    const headers: AuthHeaders = {
      'Content-Type': 'application/json'
    }

    try {
      const session = await fetchAuthSession()
      
      // Use idToken for API Gateway Cognito authorizer (not accessToken)
      if (session.tokens?.idToken) {
        headers.Authorization = `Bearer ${session.tokens.idToken.toString()}`
      }
    } catch (error) {
      console.warn('Failed to get auth session for headers:', error)
      // Don't throw error - let the API call proceed without auth header
      // The backend will handle the missing authentication appropriately
    }

    return headers
  }

  /**
   * Make an authenticated API call with automatic token attachment
   */
  static async makeAuthenticatedRequest<T>(
    url: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const authHeaders = await this.getAuthHeaders()
    
    const response = await fetch(url, {
      ...options,
      headers: {
        ...authHeaders,
        ...options.headers,
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Validate current authentication status with backend
   * Works in both local (LocalStack) and production environments
   */
  static async validateWithBackend(): Promise<{
    success: boolean
    user?: any
    stage?: string
    identity_source?: string
    error?: string
  }> {
    try {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:4566'
      const response = await this.makeAuthenticatedRequest<{
        valid: boolean
        user: any
        stage: string
        identity_source: string
      }>(`${apiBaseUrl}/auth/validate`)

      return {
        success: response.valid,
        user: response.user,
        stage: response.stage,
        identity_source: response.identity_source
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Backend validation failed'
      }
    }
  }

  static async signUp({ username, password, email, given_name, family_name }: SignUpParams) {
    try {
      const { isSignUpComplete, userId, nextStep } = await signUp({
        username,
        password,
        options: {
          userAttributes: {
            email,
            ...(given_name && { given_name }),
            ...(family_name && { family_name }),
          },
        },
      })

      return {
        success: true,
        isSignUpComplete,
        userId,
        nextStep,
      }
    } catch (error) {
      console.error('Sign up error:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Sign up failed',
      }
    }
  }

  static async redirectToSignIn() {
    await signInWithRedirect()
  }

  static async signOut() {
    try {
      await signOut()
      return { success: true }
    } catch (error) {
      console.error('Sign out error:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Sign out failed',
      }
    }
  }

  static async confirmSignUp({ username, confirmationCode }: ConfirmSignUpParams) {
    try {
      const { isSignUpComplete, nextStep } = await confirmSignUp({
        username,
        confirmationCode,
      })

      return {
        success: true,
        isSignUpComplete,
        nextStep,
      }
    } catch (error) {
      console.error('Confirm sign up error:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Confirmation failed',
      }
    }
  }

  static async resendConfirmationCode(username: string) {
    try {
      await resendSignUpCode({ username })
      return { success: true }
    } catch (error) {
      console.error('Resend confirmation code error:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Resend failed',
      }
    }
  }

  static async resetPassword({ username }: ResetPasswordParams) {
    try {
      const { nextStep } = await resetPassword({ username })
      return {
        success: true,
        nextStep,
      }
    } catch (error) {
      console.error('Reset password error:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Reset password failed',
      }
    }
  }

  static async confirmResetPassword({ username, confirmationCode, newPassword }: ConfirmResetPasswordParams) {
    try {
      await confirmResetPassword({
        username,
        confirmationCode,
        newPassword,
      })
      return { success: true }
    } catch (error) {
      console.error('Confirm reset password error:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Password reset confirmation failed',
      }
    }
  }

  static async getCurrentUser() {
    try {
      const user = await getCurrentUser()
      return {
        success: true,
        user,
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Get current user failed',
      }
    }
  }

  static async getAuthSession() {
    try {
      const session = await fetchAuthSession()
      return {
        success: true,
        session,
        tokens: session.tokens,
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Get auth session failed',
      }
    }
  }
}