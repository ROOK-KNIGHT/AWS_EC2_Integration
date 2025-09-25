import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import Login from './Login';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading, user } = useAuth();

  console.log('ProtectedRoute: User:', user);
  console.log('ProtectedRoute: isAuthenticated:', isAuthenticated);
  console.log('ProtectedRoute: isLoading:', isLoading);

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div className="login-loading">
        <div className="spinner"></div>
      </div>
    );
  }

  // If not authenticated, show login page
  if (!isAuthenticated) {
    console.log('ProtectedRoute: Redirecting to login...');
    return <Login />;
  }

  // If authenticated, render the protected content
  return children;
};

export default ProtectedRoute;
