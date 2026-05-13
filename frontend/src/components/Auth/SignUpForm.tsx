import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

interface SignUpFormData {
  email: string
  password: string
  confirmPassword: string
  given_name?: string
  family_name?: string
}

interface SignUpFormProps {
  onSwitchToSignIn: () => void
  onSignUpSuccess: (username: string) => void
}

const SignUpForm: React.FC<SignUpFormProps> = ({ onSwitchToSignIn, onSignUpSuccess }) => {
  const { signUp, isLoading } = useAuth()
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pendingApproval, setPendingApproval] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<SignUpFormData>()

  const password = watch('password')

  const onSubmit = async (data: SignUpFormData) => {
    setError(null)
    
    try {
      // When Cognito is configured with UsernameAttributes=['email'],
      // the email address should be used as the username
      const result = await signUp({
        username: data.email, // Use email as username for Cognito
        email: data.email,
        password: data.password,
        given_name: data.given_name,
        family_name: data.family_name,
      })
      
      if (result.success) {
        if (result.requiresConfirmation) {
          onSignUpSuccess(data.email)
        } else {
          // Auto-confirmed — account is pending admin approval
          setError(null)
          setPendingApproval(true)
        }
      } else {
        setError(result.error || 'Sign up failed')
      }
    } catch (error) {
      console.error('Sign up error:', error)
      setError('Sign up failed. Please try again.')
    }
  }

  if (pendingApproval) {
    return (
      <div className="w-full max-w-md text-center">
        <div className="text-5xl mb-4">✅</div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Registration received</h2>
        <p className="text-gray-600 mb-6">
          Your account has been created and is awaiting admin approval.
          You will receive an email once your account is approved.
        </p>
        <button
          type="button"
          onClick={onSwitchToSignIn}
          className="text-primary-600 hover:text-primary-500 font-medium text-sm"
        >
          Back to sign in
        </button>
      </div>
    )
  }

  return (
    <div className="w-full max-w-md">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Create your account</h2>
        <p className="text-gray-600">Join Know-It-All Tutor and start learning today</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {error && (
          <div className="bg-error-50 border border-error-200 text-error-700 px-4 py-3 rounded-md">
            {error}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="given_name" className="form-label">
              First Name
            </label>
            <input
              id="given_name"
              type="text"
              className="form-input"
              placeholder="First name"
              {...register('given_name')}
            />
          </div>
          <div>
            <label htmlFor="family_name" className="form-label">
              Last Name
            </label>
            <input
              id="family_name"
              type="text"
              className="form-input"
              placeholder="Last name"
              {...register('family_name')}
            />
          </div>
        </div>

        <div>
          <label htmlFor="email" className="form-label">
            Email Address
          </label>
          <input
            id="email"
            type="email"
            className={`form-input ${errors.email ? 'border-error-300 focus:ring-error-500' : ''}`}
            placeholder="Enter your email address"
            {...register('email', {
              required: 'Email is required',
              pattern: {
                value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                message: 'Invalid email address',
              },
            })}
          />
          {errors.email && (
            <p className="form-error">{errors.email.message}</p>
          )}
          <p className="text-xs text-gray-500 mt-1">
            Your email address will be used as your username
          </p>
        </div>

        <div>
          <label htmlFor="password" className="form-label">
            Password
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              className={`form-input pr-10 ${errors.password ? 'border-error-300 focus:ring-error-500' : ''}`}
              placeholder="Create a password"
              {...register('password', {
                required: 'Password is required',
                minLength: {
                  value: 8,
                  message: 'Password must be at least 8 characters',
                },
                pattern: {
                  value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
                  message: 'Password must contain uppercase, lowercase, number, and special character',
                },
              })}
            />
            <button
              type="button"
              className="absolute inset-y-0 right-0 pr-3 flex items-center"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4 text-gray-400" />
              ) : (
                <Eye className="h-4 w-4 text-gray-400" />
              )}
            </button>
          </div>
          {errors.password && (
            <p className="form-error">{errors.password.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="confirmPassword" className="form-label">
            Confirm Password
          </label>
          <div className="relative">
            <input
              id="confirmPassword"
              type={showConfirmPassword ? 'text' : 'password'}
              className={`form-input pr-10 ${errors.confirmPassword ? 'border-error-300 focus:ring-error-500' : ''}`}
              placeholder="Confirm your password"
              {...register('confirmPassword', {
                required: 'Please confirm your password',
                validate: (value) => value === password || 'Passwords do not match',
              })}
            />
            <button
              type="button"
              className="absolute inset-y-0 right-0 pr-3 flex items-center"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            >
              {showConfirmPassword ? (
                <EyeOff className="h-4 w-4 text-gray-400" />
              ) : (
                <Eye className="h-4 w-4 text-gray-400" />
              )}
            </button>
          </div>
          {errors.confirmPassword && (
            <p className="form-error">{errors.confirmPassword.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting || isLoading}
          className="btn btn-primary btn-lg w-full"
        >
          {isSubmitting || isLoading ? (
            <>
              <Loader2 className="animate-spin h-4 w-4 mr-2" />
              Creating account...
            </>
          ) : (
            'Create Account'
          )}
        </button>

        <div className="text-center">
          <p className="text-sm text-gray-600">
            Already have an account?{' '}
            <button
              type="button"
              onClick={onSwitchToSignIn}
              className="text-primary-600 hover:text-primary-500 font-medium"
            >
              Sign in
            </button>
          </p>
        </div>
      </form>
    </div>
  )
}

export default SignUpForm
