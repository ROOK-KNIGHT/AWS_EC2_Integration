import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from 'antd';
import 'antd/dist/antd.css';
import './App.css';

import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Portfolio from './pages/Portfolio';
import Options from './pages/Options';
import Alerts from './pages/Alerts';
import Settings from './pages/Settings';

const { Content } = Layout;

function App() {
  return (
    <AuthProvider>
      <Router>
        <ProtectedRoute>
          <Layout style={{ minHeight: '100vh' }}>
            <Sidebar />
            <Layout className="site-layout">
              <Content style={{ margin: '24px 16px', padding: 24, background: '#fff' }}>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/portfolio" element={<Portfolio />} />
                  <Route path="/options" element={<Options />} />
                  <Route path="/alerts" element={<Alerts />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </Content>
            </Layout>
          </Layout>
        </ProtectedRoute>
      </Router>
    </AuthProvider>
  );
}

export default App;
