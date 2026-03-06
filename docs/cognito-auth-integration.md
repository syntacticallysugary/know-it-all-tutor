# Frontend Cognito Authentication Integration Guide

This document provides guidance for integrating AWS Cognito authentication in the React frontend application.

## Prerequisites

Install AWS Amplify Auth library:
```bash
npm install @aws-amplify/auth @aws-amplify/core
```

## Configuration

Configure Amplify with Cognito User Pool settings:

```typescript
// src/config/amplify.ts
import { Amplify } from '@aws-amplify/core';

const amplifyConfig = {
  Auth: {
    region: process.env.REACT_APP_AWS_REGION || 'us-east-1',
    userPoolId: process.env.REACT_APP_USER_POOL_ID,
    userPoolWebClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID,
    authenticationFlowType: 'USER_SRP_AUTH',
    oauth: {
      domain: `${process.env.REACT_APP_USER_POOL_DOMAIN}.auth.${process.env.REACT_APP_AWS_REGION}.amazoncognito.com`,
      scope: ['openid', 'email', 'profile'],
      redirectSignIn: process.env.REACT_APP_REDIRECT_SIGN_IN || 'http://localhost:3000/auth/callback',
      redirectSignOut: process.env.REACT_APP_REDIRECT_SIGN_OUT || 'http://localhost:3000/auth/logout',
      responseType: 'code'
    }
  }
};

Amplify.configure(amplifyConfig);
```

## Authentication Service

Create a centralized authentication service:

```typescript
// src/services/authService.ts
import { Auth } from '@aws-amplify/auth';

export interface User {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  emailVerified: boolean;
}

export interface AuthTokens {
  accessToken: string;
  idToken: string;
  refreshToken: string;
}

class AuthService {
  async signUp(email: string, password: string, firstName?: string, lastName?: string): Promise<any> {
    const attributes: any = { email };
    
    if (firstName) attributes.given_name = firstName;
    if (lastName) attributes.family_name = lastName;

    return await Auth.signUp({
      username: email,
      password,
      attributes
    });
  }

  async confirmSignUp(email: string, code: string): Promise<any> {
    return await Auth.confirmSignUp(email, code);
  }

  async resendSignUp(email: string): Promise<any> {
    return await Auth.resendSignUp(email);
  }

  async signIn(email: string, password: string): Promise<any> {
    return await Auth.signIn(email, password);
  }

  async signOut(): Promise<void> {
    return await Auth.signOut();
  }

  async getCurrentUser(): Promise<User | null> {
    try {
      const user = await Auth.currentAuthenticatedUser();
      const attributes = user.attributes;
      
      return {
        id: attributes.sub,
        email: attributes.email,
        firstName: attributes.given_name,
        lastName: attributes.family_name,
        emailVerified: attributes.email_verified === 'true'
      };
    } catch (error) {
      return null;
    }
  }

  async getCurrentSession(): Promise<AuthTokens | null> {
    try {
      const session = await Auth.currentSession();
      
      return {
        accessToken: session.getAccessToken().getJwtToken(),
        idToken: session.getIdToken().getJwtToken(),
        refreshToken: session.getRefreshToken().getToken()
      };
    } catch (error) {
      return null;
    }
  }

  async forgotPassword(email: string): Promise<any> {
    return await Auth.forgotPassword(email);
  }

  async forgotPasswordSubmit(email: string, code: string, newPassword: string): Promise<any> {
    return await Auth.forgotPasswordSubmit(email, code, newPassword);
  }

  async changePassword(oldPassword: string, newPassword: string): Promise<any> {
    const user = await Auth.currentAuthenticatedUser();
    return await Auth.changePassword(user, oldPassword, newPassword);
  }

  async setupTOTP(): Promise<string> {
    const user = await Auth.currentAuthenticatedUser();
    return await Auth.setupTOTP(user);
  }

  async verifyTotpToken(challengeAnswer: string): Promise<any> {
    const user = await Auth.currentAuthenticatedUser();
    return await Auth.verifyTotpToken(user, challengeAnswer);
  }

  async setPreferredMFA(mfaMethod: 'SMS' | 'TOTP' | 'NOMFA'): Promise<string> {
    const user = await Auth.currentAuthenticatedUser();
    return await Auth.setPreferredMFA(user, mfaMethod);
  }
}

export const authService = new AuthService();
```

## React Context for Authentication

Create an authentication context:

```typescript
// src/contexts/AuthContext.tsx
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { authService, User } from '../services/authService';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signUp: (email: string, password: string, firstName?: string, lastName?: string) => Promise<any>;
  confirmSignUp: (email: string, code: string) => Promise<any>;
  signIn: (email: string, password: string) => Promise<any>;
  signOut: () => Promise<void>;
  forgotPassword: (email: string) => Promise<any>;
  resetPassword: (email: string, code: string, newPassword: string) => Promise<any>;
  changePassword: (oldPassword: string, newPassword: string) => Promise<any>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuthState();
  }, []);

  const checkAuthState = async () => {
    try {
      const currentUser = await authService.getCurrentUser();
      setUser(currentUser);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const signUp = async (email: string, password: string, firstName?: string, lastName?: string) => {
    const result = await authService.signUp(email, password, firstName, lastName);
    return result;
  };

  const confirmSignUp = async (email: string, code: string) => {
    const result = await authService.confirmSignUp(email, code);
    await checkAuthState(); // Refresh user state
    return result;
  };

  const signIn = async (email: string, password: string) => {
    const result = await authService.signIn(email, password);
    await checkAuthState(); // Refresh user state
    return result;
  };

  const signOut = async () => {
    await authService.signOut();
    setUser(null);
  };

  const forgotPassword = async (email: string) => {
    return await authService.forgotPassword(email);
  };

  const resetPassword = async (email: string, code: string, newPassword: string) => {
    return await authService.forgotPasswordSubmit(email, code, newPassword);
  };

  const changePassword = async (oldPassword: string, newPassword: string) => {
    return await authService.changePassword(oldPassword, newPassword);
  };

  const value: AuthContextType = {
    user,
    loading,
    signUp,
    confirmSignUp,
    signIn,
    signOut,
    forgotPassword,
    resetPassword,
    changePassword
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
```

## Authentication Components

### Login Component

```typescript
// src/components/auth/LoginForm.tsx
import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

export const LoginForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const { signIn } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await signIn(email, password);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700">
          Email
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
      
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700">
          Password
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {error && (
        <div className="text-red-600 text-sm">{error}</div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
      >
        {loading ? 'Signing in...' : 'Sign In'}
      </button>
    </form>
  );
};
```

### Registration Component

```typescript
// src/components/auth/RegisterForm.tsx
import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';

export const RegisterForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  
  const { signUp } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await signUp(email, password, firstName, lastName);
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="text-center">
        <h3 className="text-lg font-medium text-green-600">Registration Successful!</h3>
        <p className="mt-2 text-sm text-gray-600">
          Please check your email for a verification code.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="firstName" className="block text-sm font-medium text-gray-700">
            First Name
          </label>
          <input
            id="firstName"
            type="text"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        
        <div>
          <label htmlFor="lastName" className="block text-sm font-medium text-gray-700">
            Last Name
          </label>
          <input
            id="lastName"
            type="text"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      </div>
      
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700">
          Email
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
      
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700">
          Password
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {error && (
        <div className="text-red-600 text-sm">{error}</div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
      >
        {loading ? 'Creating Account...' : 'Create Account'}
      </button>
    </form>
  );
};
```

## Protected Route Component

```typescript
// src/components/auth/ProtectedRoute.tsx
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/auth/login" replace />;
  }

  return <>{children}</>;
};
```

## API Client with Automatic Token Handling

```typescript
// src/services/apiClient.ts
import { authService } from './authService';

class ApiClient {
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.REACT_APP_API_BASE_URL || 'https://api.example.com';
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    const session = await authService.getCurrentSession();
    
    if (session) {
      return {
        'Authorization': `Bearer ${session.accessToken}`,
        'Content-Type': 'application/json'
      };
    }
    
    return {
      'Content-Type': 'application/json'
    };
  }

  async get(endpoint: string): Promise<any> {
    const headers = await this.getAuthHeaders();
    
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'GET',
      headers
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  async post(endpoint: string, data: any): Promise<any> {
    const headers = await this.getAuthHeaders();
    
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  async put(endpoint: string, data: any): Promise<any> {
    const headers = await this.getAuthHeaders();
    
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  async delete(endpoint: string): Promise<any> {
    const headers = await this.getAuthHeaders();
    
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'DELETE',
      headers
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }
}

export const apiClient = new ApiClient();
```

## Environment Variables

Create a `.env` file with the following variables:

```env
REACT_APP_AWS_REGION=us-east-1
REACT_APP_USER_POOL_ID=your-user-pool-id
REACT_APP_USER_POOL_CLIENT_ID=your-user-pool-client-id
REACT_APP_USER_POOL_DOMAIN=your-user-pool-domain
REACT_APP_API_BASE_URL=https://your-api-gateway-url
REACT_APP_REDIRECT_SIGN_IN=http://localhost:3000/auth/callback
REACT_APP_REDIRECT_SIGN_OUT=http://localhost:3000/auth/logout
```

## Usage in App Component

```typescript
// src/App.tsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { LoginForm } from './components/auth/LoginForm';
import { RegisterForm } from './components/auth/RegisterForm';
import { Dashboard } from './components/Dashboard';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/auth/login" element={<LoginForm />} />
            <Route path="/auth/register" element={<RegisterForm />} />
            <Route 
              path="/dashboard" 
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              } 
            />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
```

This integration provides:

1. **Complete Cognito Authentication**: Registration, login, logout, password reset
2. **MFA Support**: TOTP and SMS-based multi-factor authentication
3. **Automatic Token Management**: Handles token refresh and API authentication
4. **Protected Routes**: Automatic redirection for unauthenticated users
5. **Error Handling**: Comprehensive error handling for all auth operations
6. **TypeScript Support**: Full type safety for all authentication operations

The frontend will automatically handle Cognito JWT tokens and integrate seamlessly with the API Gateway Cognito authorizer.