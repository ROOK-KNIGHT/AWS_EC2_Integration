import React from 'react';
import { Layout, Menu, Avatar, Dropdown, Space, Typography } from 'antd';
import { 
  DashboardOutlined, 
  PieChartOutlined, 
  LineChartOutlined, 
  BellOutlined, 
  SettingOutlined,
  UserOutlined,
  LogoutOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const { Sider } = Layout;
const { Text } = Typography;

const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/portfolio',
      icon: <PieChartOutlined />,
      label: 'Portfolio',
    },
    {
      key: '/options',
      icon: <LineChartOutlined />,
      label: 'Options',
    },
    {
      key: '/alerts',
      icon: <BellOutlined />,
      label: 'Alerts',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    },
  ];

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Profile',
      disabled: true,
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Sign Out',
      onClick: () => {
        logout();
      },
    },
  ];

  const handleMenuClick = ({ key }) => {
    navigate(key);
  };

  return (
    <Sider
      width={200}
      style={{
        overflow: 'auto',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div className="logo" style={{ padding: '16px', textAlign: 'center', borderBottom: '1px solid #303030' }}>
        <Text style={{ color: 'white', fontWeight: 'bold', fontSize: '16px' }}>
          Schwab Dashboard
        </Text>
      </div>
      
      <div style={{ flex: 1 }}>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </div>

      {/* User section at the bottom */}
      <div style={{ padding: '16px', borderTop: '1px solid #303030' }}>
        <Dropdown
          menu={{ items: userMenuItems }}
          placement="topLeft"
          trigger={['click']}
        >
          <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Avatar 
              size="small" 
              src={user?.profileObj?.imageUrl} 
              icon={<UserOutlined />}
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <Text 
                style={{ 
                  color: 'white', 
                  fontSize: '12px',
                  display: 'block',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}
              >
                {user?.profileObj?.name || user?.profileObj?.email || 'User'}
              </Text>
              <Text 
                style={{ 
                  color: '#888', 
                  fontSize: '10px',
                  display: 'block',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}
              >
                {user?.profileObj?.email}
              </Text>
            </div>
          </div>
        </Dropdown>
      </div>
    </Sider>
  );
};

export default Sidebar;
