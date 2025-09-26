# Charles Schwab API Integration - Authentication Guide

## Overview

This document details the comprehensive authentication framework implemented for the Charles Schwab API integration platform, featuring **Google Single Sign-On (SSO)**, secure session management, and protected route architecture using modern React patterns.

## 🔐 Authentication Architecture

### Multi-Layer Authentication System
```
┌─────────────────────────────────────────────────────────────┐
│                    Authentication Flow                      │
├─────────────────────────────────────────────────────────────┤
│ 1. Google OAuth2 (Primary Authentication)                  │
│ 2. JWT Token Generation (Session Management)               │
│ 3. React Context API (State Management)                    │
│ 4. Protected Routes (Access Control)                       │
│ 5. Automatic Token Refresh (Session Persistence)          │
└─────────────────────────────────────────────────────────────┘
```

## 🌐 Google SSO Integration

### OAuth2 Configuration

#### Google Cloud Console Setup
```javascript
// Required OAuth2 Settings
Client Type: Web Application
Authorized JavaScript Origins:
  - https://schwabapi.isaaccmartinez.com
  - http://localhost:3000 (development)

Authorized Redirect URIs:
  - https://schwabapi.isaaccmartinez.com/auth/google/callback
  - http://localhost:3000/auth/google/callback
```

#### Environment Variables
```bash
# Google OAuth2 Credentials
GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET

# NextAuth Configuration
NEXTAUTH_URL=https://schwabapi.isaaccmartinez.com
NEXTAUTH_SECRET=auto-generated-secure-secret
```

### NextAuth.js Integration

#### Configuration (`pages/api/auth/[...nextauth].js`)
```javascript
import NextAuth from 'next-auth'
import GoogleProvider from 'next-auth/providers/google'

export default NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      authorization: {
        params: {
          scope: 'openid email profile',
          prompt: 'consent',
          access_type: 'offline',
          response_type: 'code'
        }
      }
    })
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account) {
        token.accessToken = account.access_token
        token.refreshToken = account.refresh_token
      }
      return token
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken
      session.refreshToken = token.refreshToken
      return session
    }
  },
  session: {
    strategy: 'jwt',
    maxAge: 24 * 60 * 60, // 24 hours
  },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  }
})
```

## ⚛️ React Authentication Framework

### AuthContext Implementation

#### Context Provider (`src/contexts/AuthContext.js`)
```javascript
import React, { createContext, useContext, useEffect, useState } from 'react';
import { useSession, signIn, signOut } from 'next-auth/react';

const AuthContext = createContext({});

export const AuthProvider = ({ children }) => {
  const { data: session, status } = useSession();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (status === 'loading') return;
    
    if (session?.user) {
      setUser({
        id: session.user.email,
        name: session.user.name,
        email: session.user.email,
        image: session.user.image,
        accessToken: session.accessToken
      });
    } else {
      setUser(null);
    }
    
    setLoading(false);
  }, [session, status]);

  const login = async () => {
    try {
      await signIn('google', { 
        callbackUrl: '/',
        redirect: true 
      });
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      await signOut({ 
        callbackUrl: '/auth/signin',
        redirect: true 
      });
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
      throw error;
    }
  };

  const value = {
    user,
    login,
    logout,
    loading,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
```

### Login Component

#### Google SSO Login (`src/components/Login.js`)
```javascript
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './Login.css';

const Login = () => {
  const { login } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGoogleLogin = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      await login();
    } catch (err) {
      setError('Failed to sign in with Google. Please try again.');
      console.error('Login error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>Charles Schwab API</h1>
          <p>Trading Dashboard</p>
        </div>
        
        <div className="login-content">
          <h2>Welcome Back</h2>
          <p>Sign in to access your trading dashboard</p>
          
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}
          
          <button
            onClick={handleGoogleLogin}
            disabled={isLoading}
            className="google-login-btn"
          >
            {isLoading ? (
              <div className="loading-spinner"></div>
            ) : (
              <>
                <svg className="google-icon" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Continue with Google
              </>
            )}
          </button>
          
          <div className="login-footer">
            <p>Secure authentication powered by Google OAuth2</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
```

#### Login Styling (`src/components/Login.css`)
```css
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  width: 100%;
  max-width: 400px;
  animation: slideUp 0.6s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.login-header {
  background: #0066CC;
  color: white;
  padding: 30px 20px;
  text-align: center;
}

.login-header h1 {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
}

.login-header p {
  margin: 0;
  opacity: 0.9;
  font-size: 14px;
}

.login-content {
  padding: 40px 30px;
  text-align: center;
}

.login-content h2 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 28px;
  font-weight: 700;
}

.login-content > p {
  margin: 0 0 30px 0;
  color: #666;
  font-size: 16px;
}

.google-login-btn {
  width: 100%;
  padding: 16px 24px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  background: white;
  color: #333;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  position: relative;
}

.google-login-btn:hover {
  border-color: #4285F4;
  box-shadow: 0 4px 12px rgba(66, 133, 244, 0.15);
  transform: translateY(-2px);
}

.google-login-btn:active {
  transform: translateY(0);
}

.google-login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.google-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #4285F4;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  background: #fee;
  color: #c33;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
  border: 1px solid #fcc;
}

.login-footer {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.login-footer p {
  margin: 0;
  color: #999;
  font-size: 12px;
}

@media (max-width: 480px) {
  .login-container {
    padding: 10px;
  }
  
  .login-content {
    padding: 30px 20px;
  }
  
  .login-header {
    padding: 25px 20px;
  }
}
```

### Protected Routes

#### Route Protection Component (`src/components/ProtectedRoute.js`)
```javascript
import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import Login from './Login';

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  // Show loading spinner while checking authentication
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Show login if not authenticated
  if (!user) {
    return <Login />;
  }

  // Render protected content if authenticated
  return children;
};

export default ProtectedRoute;
```

### Application Integration

#### Main App Component (`src/App.js`)
```javascript
import React from 'react';
import { SessionProvider } from 'next-auth/react';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import './App.css';

function App({ session }) {
  return (
    <SessionProvider session={session}>
      <AuthProvider>
        <div className="App">
          <ProtectedRoute>
            <div className="app-layout">
              <Sidebar />
              <main className="main-content">
                <Dashboard />
              </main>
            </div>
          </ProtectedRoute>
        </div>
      </AuthProvider>
    </SessionProvider>
  );
}

export default App;
```

#### Sidebar with Logout (`src/components/Sidebar.js`)
```javascript
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

const Sidebar = () => {
  const { user, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
      setIsLoggingOut(false);
    }
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>Schwab API</h2>
        <div className="user-info">
          <img 
            src={user?.image || '/default-avatar.png'} 
            alt={user?.name}
            className="user-avatar"
          />
          <div className="user-details">
            <span className="user-name">{user?.name}</span>
            <span className="user-email">{user?.email}</span>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <a href="#dashboard" className="nav-item active">
          <span>📊</span> Dashboard
        </a>
        <a href="#portfolio" className="nav-item">
          <span>💼</span> Portfolio
        </a>
        <a href="#alerts" className="nav-item">
          <span>🔔</span> Alerts
        </a>
        <a href="#settings" className="nav-item">
          <span>⚙️</span> Settings
        </a>
      </nav>

      <div className="sidebar-footer">
        <button 
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="logout-btn"
        >
          {isLoggingOut ? (
            <>
              <div className="loading-spinner-small"></div>
              Signing out...
            </>
          ) : (
            <>
              <span>🚪</span> Sign Out
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
```

## 🔒 Security Features

### JWT Token Management

#### Token Structure
```javascript
{
  "sub": "user@example.com",
  "name": "John Doe",
  "email": "user@example.com",
  "picture": "https://lh3.googleusercontent.com/...",
  "iat": 1640995200,
  "exp": 1641081600,
  "jti": "unique-token-id"
}
```

#### Token Validation
```javascript
// Automatic token validation in API requests
const validateToken = (token) => {
  try {
    const decoded = jwt.verify(token, process.env.NEXTAUTH_SECRET);
    return decoded;
  } catch (error) {
    throw new Error('Invalid token');
  }
};
```

### Session Security

#### Secure Cookie Configuration
```javascript
// NextAuth.js cookie settings
cookies: {
  sessionToken: {
    name: 'next-auth.session-token',
    options: {
      httpOnly: true,
      sameSite: 'lax',
      path: '/',
      secure: process.env.NODE_ENV === 'production'
    }
  }
}
```

#### CSRF Protection
```javascript
// Built-in CSRF protection
csrf: true,
useSecureCookies: process.env.NODE_ENV === 'production'
```

## 🔄 Session Management

### Automatic Token Refresh

#### Refresh Logic
```javascript
// Token refresh implementation
const refreshAccessToken = async (token) => {
  try {
    const response = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: process.env.GOOGLE_CLIENT_ID,
        client_secret: process.env.GOOGLE_CLIENT_SECRET,
        grant_type: 'refresh_token',
        refresh_token: token.refreshToken,
      }),
    });

    const refreshedTokens = await response.json();

    if (!response.ok) {
      throw refreshedTokens;
    }

    return {
      ...token,
      accessToken: refreshedTokens.access_token,
      accessTokenExpires: Date.now() + refreshedTokens.expires_in * 1000,
      refreshToken: refreshedTokens.refresh_token ?? token.refreshToken,
    };
  } catch (error) {
    return {
      ...token,
      error: 'RefreshAccessTokenError',
    };
  }
};
```

### Session Persistence

#### Local Storage Management
```javascript
// Session state persistence
const persistSession = (session) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem('schwab-session', JSON.stringify({
      user: session.user,
      expires: session.expires
    }));
  }
};

const restoreSession = () => {
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem('schwab-session');
    return stored ? JSON.parse(stored) : null;
  }
  return null;
};
```

## 🛡️ API Authentication

### Backend API Integration

#### API Route Protection
```python
# Flask API authentication decorator
from functools import wraps
import jwt

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        try:
            # Remove 'Bearer ' prefix
            token = token.replace('Bearer ', '')
            decoded = jwt.decode(
                token, 
                current_app.config['JWT_SECRET'], 
                algorithms=['HS256']
            )
            current_user = decoded
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated_function

# Protected API endpoint
@app.route('/api/portfolio')
@require_auth
def get_portfolio(current_user):
    # Access user info from current_user
    return jsonify({'portfolio': 'data'})
```

#### API Client with Authentication
```javascript
// Authenticated API client
class SchwabAPIClient {
  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL;
  }

  async request(endpoint, options = {}) {
    const { data: session } = useSession();
    
    const config = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    if (session?.accessToken) {
      config.headers.Authorization = `Bearer ${session.accessToken}`;
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, config);
    
    if (response.status === 401) {
      // Token expired, redirect to login
      signOut({ callbackUrl: '/auth/signin' });
      return;
    }

    return response.json();
  }

  async getPortfolio() {
    return this.request('/api/portfolio');
  }

  async getAlerts() {
    return this.request('/api/alerts');
  }
}
```

## 🔧 Development Setup

### Environment Configuration

#### Development Environment
```bash
# .env.local (development)
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=development-secret-key
GOOGLE_CLIENT_ID=your-dev-client-id
GOOGLE_CLIENT_SECRET=your-dev-client-secret
```

#### Production Environment
```bash
# .env (production)
NEXTAUTH_URL=https://schwabapi.isaaccmartinez.com
NEXTAUTH_SECRET=production-secure-secret
GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET
```

### Testing Authentication

#### Unit Tests
```javascript
// Authentication context tests
import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../contexts/AuthContext';

const TestComponent = () => {
  const { user, isAuthenticated } = useAuth();
  return (
    <div>
      <span data-testid="auth-status">
        {isAuthenticated ? 'Authenticated' : 'Not Authenticated'}
      </span>
      {user && <span data-testid="user-name">{user.name}</span>}
    </div>
  );
};

test('should show not authenticated initially', () => {
  render(
    <AuthProvider>
      <TestComponent />
    </AuthProvider>
  );
  
  expect(screen.getByTestId('auth-status')).toHaveTextContent('Not Authenticated');
});
```

#### Integration Tests
```javascript
// Login flow integration test
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Login from '../components/Login';

test('should handle Google login', async () => {
  render(<Login />);
  
  const loginButton = screen.getByText('Continue with Google');
  fireEvent.click(loginButton);
  
  await waitFor(() => {
    expect(screen.getByText('Signing in...')).toBeInTheDocument();
  });
});
```

## 🚀 Deployment Considerations

### Production Security

#### HTTPS Enforcement
```javascript
// Force HTTPS in production
if (process.env.NODE_ENV === 'production' && !req.secure) {
  return res.redirect(`https://${req.headers.host}${req.url}`);
}
```

#### Security Headers
```javascript
// Security headers middleware
app.use((req, res, next) => {
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=()');
  next();
});
```

### Monitoring and Logging

#### Authentication Events
```javascript
// Log authentication events
const logAuthEvent = (event, user, details = {}) => {
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    event,
    user: user?.email,
    ip: req.ip,
    userAgent: req.headers['user-agent'],
    ...details
  }));
};

// Usage
logAuthEvent('LOGIN_SUCCESS', user);
logAuthEvent('LOGIN_FAILED', null, { error: 'Invalid credentials' });
logAuthEvent('LOGOUT', user);
```

This authentication framework provides enterprise-grade security with a seamless user experience, ensuring that only authorized users can access the Charles Schwab API integration platform while maintaining session security and providing comprehensive audit trails.
