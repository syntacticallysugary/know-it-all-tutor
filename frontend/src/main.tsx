import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Amplify } from 'aws-amplify'
import App from './App.tsx'
import './index.css'

// Configure Amplify
const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || 'us-east-1_EXAMPLE123',
      userPoolClientId: import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID || 'abcdef123456789example',
      loginWith: {
        oauth: {
          domain: import.meta.env.VITE_AUTH_DOMAIN || 'auth.syntacticallysugary.dev',
          scopes: ['openid', 'email', 'profile'],
          redirectSignIn: [import.meta.env.VITE_REDIRECT_SIGN_IN || 'https://tutor.syntacticallysugary.dev/callback'],
          redirectSignOut: [import.meta.env.VITE_REDIRECT_SIGN_OUT || 'https://tutor.syntacticallysugary.dev/'],
          responseType: 'code' as const,
        }
      }
    }
  },
  API: {
    REST: {
      'TutorAPI': {
        endpoint: import.meta.env.VITE_API_BASE_URL || 'http://localhost:4566',
        region: import.meta.env.VITE_AWS_REGION || 'us-east-1',
      }
    }
  }
}

Amplify.configure(amplifyConfig)

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)