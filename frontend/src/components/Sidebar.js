import React from 'react';
import { Layout, Menu } from 'antd';
import { 
  DashboardOutlined, 
  PieChartOutlined, 
  LineChartOutlined, 
  BellOutlined, 
  SettingOutlined 
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Sider } = Layout;

const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();

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
      }}
    >
      <div className="logo">
        Schwab Dashboard
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={handleMenuClick}
      />
    </Sider>
  );
};

export default Sidebar;
