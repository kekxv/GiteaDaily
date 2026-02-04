import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { Layout, Menu, Button } from 'antd';
import { DashboardOutlined, SettingOutlined, LogoutOutlined } from '@ant-design/icons';
import useAuthStore from './store/useAuthStore';
import Dashboard from './pages/Dashboard';
import ConfigPage from './pages/ConfigPage';
import LoginPage from './pages/LoginPage';

const { Header, Content, Sider } = Layout;

const PrivateRoute = ({ children }) => {
  const token = useAuthStore(state => state.token);
  return token ? children : <Navigate to="/login" />;
};

const MainLayout = () => {
  const logout = useAuthStore(state => state.logout);
  const location = useLocation();

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: <Link to="/">任务管理</Link> },
    { key: '/configs', icon: <SettingOutlined />, label: <Link to="/configs">配置中心</Link> },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible>
        <div style={{ height: 32, margin: 16, background: 'rgba(255, 255, 255, 0.2)', color: 'white', textAlign: 'center', lineHeight: '32px' }}>
          Gitea Reporter
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]} items={menuItems} />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 16px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
          <Button icon={<LogoutOutlined />} onClick={logout} type="text">退出登录</Button>
        </Header>
        <Content style={{ margin: '16px' }}>
          <div style={{ padding: 24, minHeight: 360, background: '#fff' }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/configs" element={<ConfigPage />} />
            </Routes>
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route 
          path="/*" 
          element={
            <PrivateRoute>
              <MainLayout />
            </PrivateRoute>
          } 
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;