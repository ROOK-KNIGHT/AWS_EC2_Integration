import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Google OAuth configuration
  const GOOGLE_CLIENT_ID = '107596960202-aecutjt4dug1h5qe2u1rc5hq4nhcmjor.apps.googleusercontent.com';

  useEffect(() => {
    console.log('AuthContext: Checking for token...');
    // Check if user is already authenticated
    const token = localStorage.getItem('google_token');
    const userData = localStorage.getItem('user_data');
    
    if (token && userData) {
      console.log('AuthContext: Token found:', !!token);
      try {
        const parsedUser = JSON.parse(userData);
        setUser(parsedUser);
        setIsAuthenticated(true);
      } catch (error) {
        console.error('Error parsing user data:', error);
        localStorage.removeItem('google_token');
        localStorage.removeItem('user_data');
      }
    } else {
      console.log('AuthContext: Token found:', false);
    }
    
    setIsLoading(false);
  }, []);

  const login = async (googleResponse) => {
    try {
      console.log('AuthContext: Processing login...', googleResponse);
      
      // Store the Google token and user data
      localStorage.setItem('google_token', googleResponse.access_token || googleResponse.credential);
      localStorage.setItem('user_data', JSON.stringify(googleResponse.profileObj || googleResponse));
      
      setUser(googleResponse.profileObj || googleResponse);
      setIsAuthenticated(true);
      
      console.log('AuthContext: Login successful');
      return true;
    } catch (error) {
      console.error('Login error:', error);
      return false;
    }
  };

  const logout = () => {
    console.log('AuthContext: Logging out...');
    localStorage.removeItem('google_token');
    localStorage.removeItem('user_data');
    setUser(null);
    setIsAuthenticated(false);
    
    // Sign out from Google
    if (window.google && window.google.accounts) {
      window.google.accounts.id.disableAutoSelect();
    }
  };

  const value = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    GOOGLE_CLIENT_ID
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
