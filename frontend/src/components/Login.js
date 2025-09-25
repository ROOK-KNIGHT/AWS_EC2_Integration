import React, { useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './Login.css';

const Login = () => {
  const { login, GOOGLE_CLIENT_ID } = useAuth();
  const googleButtonRef = useRef(null);

  useEffect(() => {
    // Load Google Identity Services script
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);

    script.onload = () => {
      if (window.google && window.google.accounts) {
        // Initialize Google Identity Services
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleCredentialResponse,
          auto_select: false,
          cancel_on_tap_outside: false,
        });

        // Render the Google Sign-In button
        if (googleButtonRef.current) {
          window.google.accounts.id.renderButton(
            googleButtonRef.current,
            {
              theme: 'outline',
              size: 'large',
              type: 'standard',
              text: 'signin_with',
              shape: 'rectangular',
              logo_alignment: 'left',
              width: 300,
            }
          );
        }

        // Display the One Tap dialog
        window.google.accounts.id.prompt();
      }
    };

    return () => {
      // Cleanup
      if (document.head.contains(script)) {
        document.head.removeChild(script);
      }
    };
  }, [GOOGLE_CLIENT_ID]);

  const handleCredentialResponse = async (response) => {
    try {
      console.log('Google credential response:', response);
      
      // Decode the JWT token to get user information
      const userInfo = parseJwt(response.credential);
      console.log('Decoded user info:', userInfo);
      
      // Create a user object similar to the old format
      const userObject = {
        credential: response.credential,
        profileObj: {
          googleId: userInfo.sub,
          imageUrl: userInfo.picture,
          email: userInfo.email,
          name: userInfo.name,
          givenName: userInfo.given_name,
          familyName: userInfo.family_name,
        }
      };
      
      const success = await login(userObject);
      if (success) {
        console.log('Login successful, redirecting...');
        // The App component will handle the redirect
      } else {
        console.error('Login failed');
        alert('Login failed. Please try again.');
      }
    } catch (error) {
      console.error('Error handling credential response:', error);
      alert('Login error. Please try again.');
    }
  };

  // Helper function to decode JWT token
  const parseJwt = (token) => {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (error) {
      console.error('Error parsing JWT:', error);
      return {};
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>Schwab Trading Dashboard</h1>
          <p>Sign in to access your trading dashboard</p>
        </div>
        
        <div className="login-content">
          <div className="google-signin-container">
            <div ref={googleButtonRef} className="google-signin-button"></div>
          </div>
          
          <div className="login-info">
            <p>
              <strong>Secure Authentication</strong><br/>
              Your data is protected with Google's secure authentication system.
            </p>
          </div>
        </div>
        
        <div className="login-footer">
          <p>© 2024 Schwab Trading Dashboard. All rights reserved.</p>
        </div>
      </div>
    </div>
  );
};

export default Login;
